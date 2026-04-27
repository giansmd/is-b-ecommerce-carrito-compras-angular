import os
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update, delete, func, desc
from database import get_db, engine, Base, AsyncSessionLocal
import models
import schemas
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta, date, time
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

def parse_date_range(start_date: str, end_date: str) -> tuple[datetime, datetime]:
    try:
        start = datetime.fromisoformat(start_date).date()
        end = datetime.fromisoformat(end_date).date()
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.") from e
    if end < start:
        raise HTTPException(status_code=400, detail="end_date must be >= start_date")
    start_dt = datetime.combine(start, time.min)
    end_dt = datetime.combine(end + timedelta(days=1), time.min)
    return start_dt, end_dt

# Create reports directory (stable path regardless of working directory)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

app.mount("/reports", StaticFiles(directory=REPORTS_DIR), name="reports")

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncSessionLocal() as session:
        # Check if users exist
        result = await session.execute(select(models.User))
        if not result.scalars().first():
            users = [
                models.User(email="admin@example.com", password_hash=get_password_hash("admin123"), role="admin"),
                models.User(email="cliente1@example.com", password_hash=get_password_hash("cliente123"), role="cliente"),
                models.User(email="cliente2@example.com", password_hash=get_password_hash("cliente123"), role="cliente"),
                models.User(email="vendedor@example.com", password_hash=get_password_hash("vendedor123"), role="admin"),
            ]
            session.add_all(users)
            await session.commit()

        # Check if products exist
        result = await session.execute(select(models.Product))
        if not result.scalars().first():
            products = [
                models.Product(name="Laptop Gamer", description="Laptop de alto rendimiento", price=1500.00, category="Electronica", stock=10),
                models.Product(name="Mouse Inalámbrico", description="Mouse ergonómico", price=25.50, category="Accesorios", stock=50),
                models.Product(name="Teclado Mecánico", description="Teclado RGB switch blue", price=80.00, category="Accesorios", stock=20),
                models.Product(name="Monitor 27' 4K", description="Monitor ultra HD", price=450.00, category="Electronica", stock=15),
                models.Product(name="Silla Ergonómica", description="Silla para oficina", price=200.00, category="Muebles", stock=5),
            ]
            session.add_all(products)
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
    start_dt, end_dt = parse_date_range(report_req.start_date, report_req.end_date)
    orders_stmt = (
        select(models.Order.id, models.User.email, models.Order.total_amount, models.Order.order_date)
        .join(models.User, models.User.id == models.Order.user_id)
        .where(models.Order.order_date >= start_dt, models.Order.order_date < end_dt)
        .order_by(models.Order.order_date.asc())
    )
    orders_result = await db.execute(orders_stmt)
    orders = orders_result.all()

    pdf_filename = f"operational_{uuid.uuid4()}.pdf"
    pdf_path = os.path.join(REPORTS_DIR, pdf_filename)
    c = canvas.Canvas(pdf_path, pagesize=letter)
    y = 760
    c.setFont("Helvetica-Bold", 14)
    c.drawString(72, y, "Reporte Operacional")
    y -= 20
    c.setFont("Helvetica", 10)
    c.drawString(72, y, f"Periodo: {report_req.start_date} a {report_req.end_date}")
    y -= 16
    c.drawString(72, y, f"Generado: {datetime.utcnow().isoformat(timespec='seconds')}Z")
    y -= 24
    c.setFont("Helvetica-Bold", 11)
    c.drawString(72, y, "Pedidos")
    y -= 18

    c.setFont("Helvetica", 9)
    if not orders:
        c.drawString(72, y, "No hay pedidos en el rango seleccionado.")
        y -= 14
    else:
        for order_id, email, total_amount, order_date in orders:
            line = f"#{order_id} | {order_date.isoformat(sep=' ', timespec='seconds')} | {email} | Total: {float(total_amount):.2f}"
            c.drawString(72, y, line)
            y -= 12
            if y < 72:
                c.showPage()
                y = 760
                c.setFont("Helvetica", 9)
    c.save()
    return {"pdf_url": f"/reports/{pdf_filename}"}

@app.post("/api/reports/management")
async def generate_management_report(db: AsyncSession = Depends(get_db)):
    totals_stmt = select(
        func.count(models.Order.id),
        func.coalesce(func.sum(models.Order.total_amount), 0),
        func.coalesce(func.avg(models.Order.total_amount), 0),
    )
    totals_row = (await db.execute(totals_stmt)).one()
    total_orders = int(totals_row[0] or 0)
    total_revenue = float(totals_row[1] or 0)
    avg_ticket = float(totals_row[2] or 0)

    top_products_stmt = (
        select(models.Product.name, func.coalesce(func.sum(models.OrderDetail.quantity), 0).label("ventas"))
        .join(models.OrderDetail, models.OrderDetail.product_id == models.Product.id)
        .group_by(models.Product.name)
        .order_by(desc("ventas"))
        .limit(10)
    )
    top_products = (await db.execute(top_products_stmt)).all()

    category_sales_stmt = (
        select(
            func.coalesce(models.Product.category, "Sin categoría").label("categoria"),
            func.coalesce(func.sum(models.OrderDetail.quantity * models.OrderDetail.price), 0).label("ingresos"),
        )
        .join(models.OrderDetail, models.OrderDetail.product_id == models.Product.id)
        .group_by("categoria")
        .order_by(desc("ingresos"))
        .limit(10)
    )
    top_categories = (await db.execute(category_sales_stmt)).all()

    pdf_filename = f"management_{uuid.uuid4()}.pdf"
    pdf_path = os.path.join(REPORTS_DIR, pdf_filename)
    c = canvas.Canvas(pdf_path, pagesize=letter)
    y = 760
    c.setFont("Helvetica-Bold", 14)
    c.drawString(72, y, "Reporte Gerencial")
    y -= 20
    c.setFont("Helvetica", 10)
    c.drawString(72, y, f"Generado: {datetime.utcnow().isoformat(timespec='seconds')}Z")
    y -= 24

    c.setFont("Helvetica-Bold", 11)
    c.drawString(72, y, "Resumen")
    y -= 18
    c.setFont("Helvetica", 10)
    c.drawString(72, y, f"Pedidos totales: {total_orders}")
    y -= 14
    c.drawString(72, y, f"Ingresos totales: {total_revenue:.2f}")
    y -= 14
    c.drawString(72, y, f"Ticket promedio: {avg_ticket:.2f}")
    y -= 22

    c.setFont("Helvetica-Bold", 11)
    c.drawString(72, y, "Top Productos (por unidades)")
    y -= 18
    c.setFont("Helvetica", 10)
    if not top_products:
        c.drawString(72, y, "Sin ventas registradas.")
        y -= 14
    else:
        for name, ventas in top_products:
            c.drawString(72, y, f"- {name}: {int(ventas or 0)}")
            y -= 14
            if y < 72:
                c.showPage()
                y = 760
                c.setFont("Helvetica", 10)

    y -= 8
    c.setFont("Helvetica-Bold", 11)
    c.drawString(72, y, "Top Categorías (por ingresos)")
    y -= 18
    c.setFont("Helvetica", 10)
    if not top_categories:
        c.drawString(72, y, "Sin ventas registradas.")
        y -= 14
    else:
        for categoria, ingresos in top_categories:
            c.drawString(72, y, f"- {categoria}: {float(ingresos or 0):.2f}")
            y -= 14
            if y < 72:
                c.showPage()
                y = 760
                c.setFont("Helvetica", 10)
    c.save()
    return {"pdf_url": f"/reports/{pdf_filename}"}

# Stats
@app.get("/api/stats/daily-sales")
async def daily_sales(db: AsyncSession = Depends(get_db)):
    today = datetime.utcnow().date()
    start_dt = datetime.combine(today, time.min)
    end_dt = start_dt + timedelta(days=1)

    today_stmt = select(
        func.count(models.Order.id),
        func.coalesce(func.sum(models.Order.total_amount), 0),
    ).where(models.Order.order_date >= start_dt, models.Order.order_date < end_dt)
    today_row = (await db.execute(today_stmt)).one()
    orders_today = int(today_row[0] or 0)
    revenue_today = float(today_row[1] or 0)

    total_stmt = select(func.coalesce(func.sum(models.Order.total_amount), 0))
    total_revenue = float((await db.execute(total_stmt)).scalar_one() or 0)

    return {
        "total_ventas_hoy": orders_today,
        "ingresos_hoy": revenue_today,
        "ingresos_totales": total_revenue,
    }

@app.get("/api/stats/top-products")
async def top_products(db: AsyncSession = Depends(get_db)):
    stmt = (
        select(models.Product.name, func.coalesce(func.sum(models.OrderDetail.quantity), 0).label("ventas"))
        .join(models.OrderDetail, models.OrderDetail.product_id == models.Product.id)
        .group_by(models.Product.name)
        .order_by(desc("ventas"))
        .limit(10)
    )
    rows = (await db.execute(stmt)).all()
    return [{"producto": name, "ventas": int(ventas or 0)} for name, ventas in rows]

@app.get("/api/stats/user-metrics")
async def user_metrics(db: AsyncSession = Depends(get_db)):
    orders_count_stmt = select(func.count(models.Order.id))
    total_orders = int((await db.execute(orders_count_stmt)).scalar_one() or 0)

    distinct_users_stmt = select(func.count(func.distinct(models.Order.user_id)))
    users_with_orders = int((await db.execute(distinct_users_stmt)).scalar_one() or 0)

    avg_stmt = select(func.coalesce(func.avg(models.Order.total_amount), 0))
    avg_order_total = float((await db.execute(avg_stmt)).scalar_one() or 0)

    frequency = (total_orders / users_with_orders) if users_with_orders else 0
    return {
        "promedio_compra_usuario": avg_order_total,
        "frecuencia_compras": round(frequency, 2),
    }

@app.get("/api/stats/category-sales")
async def category_sales(db: AsyncSession = Depends(get_db)):
    stmt = (
        select(
            func.coalesce(models.Product.category, "Sin categoría").label("categoria"),
            func.coalesce(func.sum(models.OrderDetail.quantity), 0).label("ventas"),
            func.coalesce(func.sum(models.OrderDetail.quantity * models.OrderDetail.price), 0).label("ingresos"),
        )
        .join(models.OrderDetail, models.OrderDetail.product_id == models.Product.id)
        .group_by("categoria")
        .order_by(desc("ingresos"))
    )
    rows = (await db.execute(stmt)).all()
    return [
        {"categoria": categoria, "ventas": int(ventas or 0), "ingresos": float(ingresos or 0)}
        for categoria, ventas, ingresos in rows
    ]
