import os
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update, delete, func
from database import get_db, engine, Base, AsyncSessionLocal
import models
import schemas
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import uuid

# Security
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440 # 24 hours

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI(title="Shopping Cart API")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helper functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str | None = payload.get("sub")
        if not email:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    result = await db.execute(select(models.User).where(models.User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        raise credentials_exception
    return user

async def require_admin(current_user: models.User = Depends(get_current_user)) -> models.User:
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return current_user

# Create reports directory
if not os.path.exists("reports"):
    os.makedirs("reports")

app.mount("/reports", StaticFiles(directory="reports"), name="reports")

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    admin_email = os.getenv("ADMIN_EMAIL")
    admin_password = os.getenv("ADMIN_PASSWORD")
    if admin_email and admin_password:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(models.User).where(models.User.email == admin_email))
            existing = result.scalar_one_or_none()
            if not existing:
                admin = models.User(
                    email=admin_email,
                    password_hash=get_password_hash(admin_password),
                    role="admin",
                )
                session.add(admin)
                await session.commit()

# Endpoints
@app.post("/api/auth/register", response_model=schemas.UserResponse)
async def register(user: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.User).where(models.User.email == user.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    new_user = models.User(
        email=user.email,
        password_hash=get_password_hash(user.password),
        role=user.role
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

@app.post("/api/auth/login")
async def login(user_credentials: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.User).where(models.User.email == user_credentials.email))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(user_credentials.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    
    access_token = create_access_token(data={"sub": user.email, "role": user.role, "user_id": user.id})
    return {"access_token": access_token, "role": user.role}

# Products
@app.get("/api/products", response_model=list[schemas.ProductResponse])
async def get_products(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Product))
    return result.scalars().all()

@app.post("/api/products", response_model=schemas.ProductResponse)
async def create_product(
    product: schemas.ProductBase,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    new_product = models.Product(**product.dict())
    db.add(new_product)
    await db.commit()
    await db.refresh(new_product)
    return new_product

@app.put("/api/products/{product_id}", response_model=schemas.ProductResponse)
async def update_product(
    product_id: int,
    product: schemas.ProductUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    result = await db.execute(select(models.Product).where(models.Product.id == product_id))
    existing = result.scalar_one_or_none()
    if not existing:
        raise HTTPException(status_code=404, detail="Product not found")
    updates = product.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(existing, key, value)
    await db.commit()
    await db.refresh(existing)
    return existing

@app.delete("/api/products/{product_id}")
async def delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    result = await db.execute(select(models.Product).where(models.Product.id == product_id))
    existing = result.scalar_one_or_none()
    if not existing:
        raise HTTPException(status_code=404, detail="Product not found")
    await db.delete(existing)
    await db.commit()
    return {"message": "Producto eliminado"}

# Cart
@app.post("/api/cart/add")
async def add_to_cart(item: schemas.CartItemAdd, db: AsyncSession = Depends(get_db)):
    # Verify product
    result = await db.execute(select(models.Product).where(models.Product.id == item.product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(404, "Product not found")
    if product.stock < item.quantity:
        raise HTTPException(400, "Insufficient stock")
    
    # Get or create active cart
    result = await db.execute(select(models.Cart).where(models.Cart.user_id == item.user_id, models.Cart.status == "activo"))
    cart = result.scalar_one_or_none()
    if not cart:
        cart = models.Cart(user_id=item.user_id)
        db.add(cart)
        await db.flush()
    
    # Add item
    new_item = models.CartItem(
        cart_id=cart.id,
        product_id=item.product_id,
        quantity=item.quantity,
        price_at_time=product.price
    )
    db.add(new_item)
    await db.commit()
    return {"message": "Producto agregado al carrito", "cart_id": cart.id}

@app.delete("/api/cart/remove/{item_id}")
async def remove_from_cart(item_id: int, db: AsyncSession = Depends(get_db)):
    await db.execute(delete(models.CartItem).where(models.CartItem.id == item_id))
    await db.commit()
    return {"message": "Producto eliminado"}

@app.post("/api/cart/checkout")
async def checkout(data: dict, db: AsyncSession = Depends(get_db)):
    user_id = data.get("user_id")
    result = await db.execute(select(models.Cart).where(models.Cart.user_id == user_id, models.Cart.status == "activo"))
    cart = result.scalar_one_or_none()
    if not cart:
        raise HTTPException(404, "No active cart found")
    
    # Calculate total
    result = await db.execute(select(models.CartItem).where(models.CartItem.cart_id == cart.id))
    items = result.scalars().all()
    total = sum(item.quantity * item.price_at_time for item in items)
    
    # Create order
    order = models.Order(user_id=user_id, total_amount=total)
    db.add(order)
    await db.flush()
    
    # Create order details
    for item in items:
        detail = models.OrderDetail(
            order_id=order.id,
            product_id=item.product_id,
            quantity=item.quantity,
            price=item.price_at_time
        )
        db.add(detail)
        # Update stock
        await db.execute(update(models.Product).where(models.Product.id == item.product_id).values(stock=models.Product.stock - item.quantity))
    
    # Close cart
    cart.status = "procesado"
    await db.commit()
    return {"order_id": order.id, "total": total, "message": "Compra realizada"}

# Reports
@app.post("/api/reports/operational")
async def generate_operational_report(report_req: schemas.ReportRequest, db: AsyncSession = Depends(get_db)):
    pdf_filename = f"operational_{uuid.uuid4()}.pdf"
    pdf_path = os.path.join("reports", pdf_filename)
    c = canvas.Canvas(pdf_path, pagesize=letter)
    c.drawString(100, 750, f"Reporte Operacional: {report_req.start_date} a {report_req.end_date}")
    c.save()
    return {"pdf_url": f"/reports/{pdf_filename}"}

@app.post("/api/reports/management")
async def generate_management_report(db: AsyncSession = Depends(get_db)):
    pdf_filename = f"management_{uuid.uuid4()}.pdf"
    pdf_path = os.path.join("reports", pdf_filename)
    c = canvas.Canvas(pdf_path, pagesize=letter)
    c.drawString(100, 750, "Reporte Gerencial")
    c.save()
    return {"pdf_url": f"/reports/{pdf_filename}"}

# Stats
@app.get("/api/stats/daily-sales")
async def daily_sales(db: AsyncSession = Depends(get_db)):
    return {"total_ventas_hoy": 1500, "ingresos_totales": 50000}

@app.get("/api/stats/top-products")
async def top_products(db: AsyncSession = Depends(get_db)):
    return [{"producto": "A", "ventas": 50}, {"producto": "B", "ventas": 30}]

@app.get("/api/stats/user-metrics")
async def user_metrics(db: AsyncSession = Depends(get_db)):
    return {"promedio_compra_usuario": 250, "frecuencia_compras": 2.5}
