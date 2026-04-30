import os
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update, delete, func, desc, text
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


PAGE_WIDTH, PAGE_HEIGHT = letter
PDF_MARGIN_X = 56
PDF_MARGIN_BOTTOM = 56


def _fmt_money(value: float) -> str:
    return f"S/ {value:,.2f}"


def _draw_report_header(c: canvas.Canvas, title: str, subtitle: str, generated_at: str, page_number: int) -> float:
    c.setFillColorRGB(0.09, 0.18, 0.36)
    c.rect(0, PAGE_HEIGHT - 90, PAGE_WIDTH, 90, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 17)
    c.drawString(PDF_MARGIN_X, PAGE_HEIGHT - 42, title)
    c.setFont("Helvetica", 9)
    c.drawString(PDF_MARGIN_X, PAGE_HEIGHT - 60, subtitle)
    c.drawRightString(PAGE_WIDTH - PDF_MARGIN_X, PAGE_HEIGHT - 60, generated_at)

    c.setStrokeColorRGB(0.77, 0.82, 0.92)
    c.setLineWidth(1)
    c.line(PDF_MARGIN_X, PAGE_HEIGHT - 94, PAGE_WIDTH - PDF_MARGIN_X, PAGE_HEIGHT - 94)
    c.setFont("Helvetica", 8)
    c.setFillColorRGB(0.42, 0.47, 0.56)
    c.drawRightString(PAGE_WIDTH - PDF_MARGIN_X, PAGE_HEIGHT - 106, f"Pagina {page_number}")
    c.setFillColorRGB(0, 0, 0)
    return PAGE_HEIGHT - 128


def _draw_report_footer(c: canvas.Canvas, label: str, page_number: int) -> None:
    c.setStrokeColorRGB(0.82, 0.84, 0.88)
    c.line(PDF_MARGIN_X, PDF_MARGIN_BOTTOM - 8, PAGE_WIDTH - PDF_MARGIN_X, PDF_MARGIN_BOTTOM - 8)
    c.setFont("Helvetica", 8)
    c.setFillColorRGB(0.42, 0.47, 0.56)
    c.drawString(PDF_MARGIN_X, PDF_MARGIN_BOTTOM - 22, label)
    c.drawRightString(PAGE_WIDTH - PDF_MARGIN_X, PDF_MARGIN_BOTTOM - 22, f"Pagina {page_number}")
    c.setFillColorRGB(0, 0, 0)


def _draw_section_title(c: canvas.Canvas, y: float, title: str) -> float:
    c.setFillColorRGB(0.15, 0.20, 0.31)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(PDF_MARGIN_X, y, title)
    c.setStrokeColorRGB(0.84, 0.87, 0.92)
    c.line(PDF_MARGIN_X, y - 4, PAGE_WIDTH - PDF_MARGIN_X, y - 4)
    c.setFillColorRGB(0, 0, 0)
    return y - 18


def _draw_kpi_card(c: canvas.Canvas, x: float, y: float, width: float, height: float, label: str, value: str, tone: str) -> None:
    tones = {
        "blue": ((0.91, 0.95, 1.0), (0.12, 0.31, 0.62)),
        "green": ((0.90, 0.98, 0.94), (0.08, 0.44, 0.25)),
        "orange": ((1.0, 0.95, 0.89), (0.67, 0.36, 0.02)),
        "purple": ((0.95, 0.92, 1.0), (0.34, 0.20, 0.57)),
    }
    fill_color, text_color = tones.get(tone, tones["blue"])
    c.setFillColorRGB(*fill_color)
    c.setStrokeColorRGB(0.80, 0.84, 0.90)
    c.roundRect(x, y - height, width, height, 8, fill=1, stroke=1)
    c.setFillColorRGB(*text_color)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x + 10, y - 16, label)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(x + 10, y - 36, value)
    c.setFillColorRGB(0, 0, 0)


def _draw_table_header(c: canvas.Canvas, y: float, columns: list[tuple[str, float]]) -> float:
    c.setFillColorRGB(0.92, 0.94, 0.98)
    c.rect(PDF_MARGIN_X, y - 14, PAGE_WIDTH - (2 * PDF_MARGIN_X), 16, fill=1, stroke=0)
    c.setFillColorRGB(0.18, 0.23, 0.33)
    c.setFont("Helvetica-Bold", 9)
    cursor_x = PDF_MARGIN_X + 6
    for label, width in columns:
        c.drawString(cursor_x, y - 4, label)
        cursor_x += width
    c.setFillColorRGB(0, 0, 0)
    return y - 20


def _low_stock_level(stock: int) -> str:
    if stock <= 5:
        return "CRITICO"
    return "ALERTA"


DEFAULT_PRODUCTS = [
    {
        "name": "Laptop Gamer",
        "description": "Laptop de alto rendimiento",
        "price": 1500.00,
        "category": "Electronica",
        "stock": 10,
        "image_url": "https://images.unsplash.com/photo-1498050108023-c5249f4df085?auto=format&fit=crop&w=1200&q=80",
    },
    {
        "name": "Mouse Inalámbrico",
        "description": "Mouse ergonómico",
        "price": 25.50,
        "category": "Accesorios",
        "stock": 50,
        "image_url": "https://images.unsplash.com/photo-1527814050087-3793815479db?auto=format&fit=crop&w=1200&q=80",
    },
    {
        "name": "Teclado Mecánico",
        "description": "Teclado RGB switch blue",
        "price": 80.00,
        "category": "Accesorios",
        "stock": 20,
        "image_url": "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?auto=format&fit=crop&w=1200&q=80",
    },
    {
        "name": "Monitor 27' 4K",
        "description": "Monitor ultra HD",
        "price": 450.00,
        "category": "Electronica",
        "stock": 15,
        "image_url": "https://images.unsplash.com/photo-1527430253228-e93688616381?auto=format&fit=crop&w=1200&q=80",
    },
    {
        "name": "Silla Ergonómica",
        "description": "Silla para oficina",
        "price": 200.00,
        "category": "Muebles",
        "stock": 5,
        "image_url": "https://images.unsplash.com/photo-1505843513577-22bb7d21e455?auto=format&fit=crop&w=1200&q=80",
    },
]


async def ensure_product_image_column(conn):
    await conn.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS image_url VARCHAR(500)"))


async def seed_product_images(session):
    for product_data in DEFAULT_PRODUCTS:
        await session.execute(
            update(models.Product)
            .where(
                models.Product.name == product_data["name"],
                models.Product.image_url.is_(None),
            )
            .values(image_url=product_data["image_url"])
        )
    await session.commit()

# Create reports directory (stable path regardless of working directory)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

app.mount("/reports", StaticFiles(directory=REPORTS_DIR), name="reports")

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await ensure_product_image_column(conn)
    
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
            products = [models.Product(**product_data) for product_data in DEFAULT_PRODUCTS]
            session.add_all(products)
            await session.commit()
        else:
            await seed_product_images(session)

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
    new_product = models.Product(**product.model_dump())
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

@app.get("/api/orders/admin", response_model=list[schemas.OrderAdminListItem])
async def list_orders_admin(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    items_count_subquery = (
        select(
            models.OrderDetail.order_id.label("order_id"),
            func.count(models.OrderDetail.id).label("items_count"),
        )
        .group_by(models.OrderDetail.order_id)
        .subquery()
    )

    stmt = (
        select(
            models.Order.id,
            models.Order.user_id,
            models.User.email,
            models.Order.total_amount,
            models.Order.status,
            models.Order.order_date,
            func.coalesce(items_count_subquery.c.items_count, 0),
        )
        .join(models.User, models.User.id == models.Order.user_id)
        .outerjoin(items_count_subquery, items_count_subquery.c.order_id == models.Order.id)
        .order_by(models.Order.order_date.desc())
    )
    rows = (await db.execute(stmt)).all()
    return [
        {
            "id": order_id,
            "user_id": user_id,
            "customer_email": email,
            "total_amount": total_amount,
            "status": status,
            "order_date": order_date,
            "items_count": int(items_count or 0),
        }
        for order_id, user_id, email, total_amount, status, order_date, items_count in rows
    ]

@app.get("/api/orders/admin/{order_id}", response_model=schemas.OrderAdminDetail)
async def get_order_admin_detail(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    order_stmt = (
        select(
            models.Order.id,
            models.Order.user_id,
            models.User.email,
            models.Order.total_amount,
            models.Order.status,
            models.Order.order_date,
        )
        .join(models.User, models.User.id == models.Order.user_id)
        .where(models.Order.id == order_id)
    )
    order_row = (await db.execute(order_stmt)).one_or_none()
    if not order_row:
        raise HTTPException(status_code=404, detail="Order not found")

    details_stmt = (
        select(
            models.OrderDetail.id,
            models.OrderDetail.product_id,
            models.Product.name,
            models.OrderDetail.quantity,
            models.OrderDetail.price,
        )
        .join(models.Product, models.Product.id == models.OrderDetail.product_id)
        .where(models.OrderDetail.order_id == order_id)
        .order_by(models.OrderDetail.id.asc())
    )
    detail_rows = (await db.execute(details_stmt)).all()
    items = [
        {
            "id": detail_id,
            "product_id": product_id,
            "product_name": product_name,
            "quantity": quantity,
            "price": price,
            "subtotal": quantity * price,
        }
        for detail_id, product_id, product_name, quantity, price in detail_rows
    ]

    return {
        "id": order_row[0],
        "user_id": order_row[1],
        "customer_email": order_row[2],
        "total_amount": order_row[3],
        "status": order_row[4],
        "order_date": order_row[5],
        "items": items,
    }

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

    period_totals_stmt = select(
        func.count(models.Order.id),
        func.coalesce(func.sum(models.Order.total_amount), 0),
        func.coalesce(func.avg(models.Order.total_amount), 0),
    ).where(models.Order.order_date >= start_dt, models.Order.order_date < end_dt)
    period_totals = (await db.execute(period_totals_stmt)).one()
    orders_count = int(period_totals[0] or 0)
    period_revenue = float(period_totals[1] or 0)
    period_avg_ticket = float(period_totals[2] or 0)

    today = datetime.utcnow().date()
    today_start_dt = datetime.combine(today, time.min)
    today_end_dt = today_start_dt + timedelta(days=1)
    today_stmt = select(
        func.count(models.Order.id),
        func.coalesce(func.sum(models.Order.total_amount), 0),
    ).where(models.Order.order_date >= today_start_dt, models.Order.order_date < today_end_dt)
    today_row = (await db.execute(today_stmt)).one()
    revenue_today = float(today_row[1] or 0)

    low_stock_stmt = (
        select(models.Product.name, models.Product.category, models.Product.stock)
        .where(models.Product.stock < 20)
        .order_by(models.Product.stock.asc(), models.Product.name.asc())
    )
    low_stock_rows = (await db.execute(low_stock_stmt)).all()

    pdf_filename = f"operational_{uuid.uuid4()}.pdf"
    pdf_path = os.path.join(REPORTS_DIR, pdf_filename)
    c = canvas.Canvas(pdf_path, pagesize=letter)
    generated_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    page_number = 1
    y = _draw_report_header(
        c,
        "Reporte Operacional",
        f"Periodo analizado: {report_req.start_date} a {report_req.end_date}",
        generated_at,
        page_number,
    )

    def next_page(current_page: int) -> tuple[int, float]:
        _draw_report_footer(c, "Sistema Ecommerce - Reporte operacional", current_page)
        c.showPage()
        new_page = current_page + 1
        new_y = _draw_report_header(
            c,
            "Reporte Operacional",
            f"Periodo analizado: {report_req.start_date} a {report_req.end_date}",
            generated_at,
            new_page,
        )
        return new_page, new_y

    def ensure_space(current_y: float, needed: float, current_page: int) -> tuple[float, int]:
        if current_y - needed < PDF_MARGIN_BOTTOM + 20:
            current_page, current_y = next_page(current_page)
        return current_y, current_page

    y = _draw_section_title(c, y, "Resumen Ejecutivo")
    card_gap = 10
    card_width = (PAGE_WIDTH - (2 * PDF_MARGIN_X) - (card_gap * 1)) / 2
    card_height = 46
    _draw_kpi_card(c, PDF_MARGIN_X, y, card_width, card_height, "Pedidos del periodo", str(orders_count), "blue")
    _draw_kpi_card(
        c,
        PDF_MARGIN_X + card_width + card_gap,
        y,
        card_width,
        card_height,
        "Ingresos del periodo",
        _fmt_money(period_revenue),
        "green",
    )
    y -= card_height + 10
    _draw_kpi_card(c, PDF_MARGIN_X, y, card_width, card_height, "Ticket promedio", _fmt_money(period_avg_ticket), "purple")
    _draw_kpi_card(
        c,
        PDF_MARGIN_X + card_width + card_gap,
        y,
        card_width,
        card_height,
        "Ingresos de hoy",
        _fmt_money(revenue_today),
        "orange",
    )
    y -= card_height + 20

    y, page_number = ensure_space(y, 120, page_number)
    y = _draw_section_title(c, y, "Detalle de Pedidos")
    columns = [("Pedido", 52), ("Fecha", 120), ("Cliente", 210), ("Total", 90)]
    y = _draw_table_header(c, y, columns)
    c.setFont("Helvetica", 9)

    if not orders:
        c.drawString(PDF_MARGIN_X + 6, y - 2, "No hay pedidos en el rango seleccionado.")
        y -= 16
    else:
        row_index = 0
        for order_id, email, total_amount, order_date in orders:
            y, page_number = ensure_space(y, 20, page_number)
            if row_index % 2 == 0:
                c.setFillColorRGB(0.98, 0.99, 1.0)
                c.rect(PDF_MARGIN_X, y - 11, PAGE_WIDTH - (2 * PDF_MARGIN_X), 13, fill=1, stroke=0)
                c.setFillColorRGB(0, 0, 0)
            c.drawString(PDF_MARGIN_X + 6, y - 1, f"#{order_id}")
            c.drawString(PDF_MARGIN_X + 58, y - 1, order_date.strftime("%Y-%m-%d %H:%M"))
            safe_email = email if len(email) <= 34 else f"{email[:31]}..."
            c.drawString(PDF_MARGIN_X + 178, y - 1, safe_email)
            c.drawRightString(PAGE_WIDTH - PDF_MARGIN_X - 8, y - 1, _fmt_money(float(total_amount)))
            y -= 14
            row_index += 1

    y -= 10
    y, page_number = ensure_space(y, 120, page_number)
    y = _draw_section_title(c, y, "Productos de Bajo Stock (stock < 20)")
    low_columns = [("Producto", 250), ("Categoria", 120), ("Stock", 60), ("Nivel", 70)]
    y = _draw_table_header(c, y, low_columns)
    c.setFont("Helvetica", 9)

    if not low_stock_rows:
        c.drawString(PDF_MARGIN_X + 6, y - 1, "No hay productos en nivel de alerta.")
        y -= 14
    else:
        row_index = 0
        for product_name, category, stock in low_stock_rows:
            y, page_number = ensure_space(y, 20, page_number)
            if row_index % 2 == 0:
                c.setFillColorRGB(1.0, 0.98, 0.95)
                c.rect(PDF_MARGIN_X, y - 11, PAGE_WIDTH - (2 * PDF_MARGIN_X), 13, fill=1, stroke=0)
                c.setFillColorRGB(0, 0, 0)
            level = _low_stock_level(int(stock or 0))
            c.drawString(PDF_MARGIN_X + 6, y - 1, product_name[:40])
            c.drawString(PDF_MARGIN_X + 256, y - 1, (category or "Sin categoria")[:18])
            c.drawString(PDF_MARGIN_X + 378, y - 1, str(int(stock or 0)))
            if level == "CRITICO":
                c.setFillColorRGB(0.72, 0.16, 0.16)
            else:
                c.setFillColorRGB(0.75, 0.42, 0.08)
            c.drawString(PDF_MARGIN_X + 438, y - 1, level)
            c.setFillColorRGB(0, 0, 0)
            y -= 14
            row_index += 1

    y -= 8
    y, page_number = ensure_space(y, 62, page_number)
    y = _draw_section_title(c, y, "Recomendaciones")
    c.setFont("Helvetica", 9)
    c.drawString(PDF_MARGIN_X + 4, y, "- Priorizar reposicion de productos en estado CRITICO (stock <= 5).")
    y -= 14
    c.drawString(PDF_MARGIN_X + 4, y, "- Programar compra semanal para productos en estado ALERTA (stock 6-19).")
    y -= 14
    c.drawString(PDF_MARGIN_X + 4, y, "- Revisar campañas sobre productos top para sostener margen e ingresos.")
    y -= 16

    _draw_report_footer(c, "Sistema Ecommerce - Reporte operacional", page_number)
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

    today = datetime.utcnow().date()
    today_start_dt = datetime.combine(today, time.min)
    today_end_dt = today_start_dt + timedelta(days=1)
    today_stmt = select(
        func.count(models.Order.id),
        func.coalesce(func.sum(models.Order.total_amount), 0),
    ).where(models.Order.order_date >= today_start_dt, models.Order.order_date < today_end_dt)
    today_row = (await db.execute(today_stmt)).one()
    orders_today = int(today_row[0] or 0)
    revenue_today = float(today_row[1] or 0)

    distinct_users_stmt = select(func.count(func.distinct(models.Order.user_id)))
    users_with_orders = int((await db.execute(distinct_users_stmt)).scalar_one() or 0)
    frequency = (total_orders / users_with_orders) if users_with_orders else 0

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

    low_stock_stmt = (
        select(models.Product.name, models.Product.category, models.Product.stock)
        .where(models.Product.stock < 20)
        .order_by(models.Product.stock.asc(), models.Product.name.asc())
    )
    low_stock_rows = (await db.execute(low_stock_stmt)).all()

    pdf_filename = f"management_{uuid.uuid4()}.pdf"
    pdf_path = os.path.join(REPORTS_DIR, pdf_filename)
    c = canvas.Canvas(pdf_path, pagesize=letter)
    generated_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    page_number = 1
    y = _draw_report_header(
        c,
        "Reporte Gerencial",
        "Vista ejecutiva de rendimiento comercial y operativo",
        generated_at,
        page_number,
    )

    def next_page(current_page: int) -> tuple[int, float]:
        _draw_report_footer(c, "Sistema Ecommerce - Reporte gerencial", current_page)
        c.showPage()
        new_page = current_page + 1
        new_y = _draw_report_header(
            c,
            "Reporte Gerencial",
            "Vista ejecutiva de rendimiento comercial y operativo",
            generated_at,
            new_page,
        )
        return new_page, new_y

    def ensure_space(current_y: float, needed: float, current_page: int) -> tuple[float, int]:
        if current_y - needed < PDF_MARGIN_BOTTOM + 20:
            current_page, current_y = next_page(current_page)
        return current_y, current_page

    y = _draw_section_title(c, y, "Indicadores Clave")
    card_gap = 8
    card_width = (PAGE_WIDTH - (2 * PDF_MARGIN_X) - (card_gap * 3)) / 4
    card_height = 46
    _draw_kpi_card(c, PDF_MARGIN_X, y, card_width, card_height, "Ventas hoy", str(orders_today), "blue")
    _draw_kpi_card(
        c, PDF_MARGIN_X + (card_width + card_gap), y, card_width, card_height, "Ingresos hoy", _fmt_money(revenue_today), "green"
    )
    _draw_kpi_card(
        c,
        PDF_MARGIN_X + (2 * (card_width + card_gap)),
        y,
        card_width,
        card_height,
        "Ingresos totales",
        _fmt_money(total_revenue),
        "orange",
    )
    _draw_kpi_card(
        c,
        PDF_MARGIN_X + (3 * (card_width + card_gap)),
        y,
        card_width,
        card_height,
        "Frecuencia",
        f"{frequency:.2f}",
        "purple",
    )
    y -= card_height + 22

    y, page_number = ensure_space(y, 140, page_number)
    y = _draw_section_title(c, y, "Top Productos (unidades)")
    y = _draw_table_header(c, y, [("Rank", 44), ("Producto", 322), ("Ventas", 90)])
    c.setFont("Helvetica", 9)
    if not top_products:
        c.drawString(PDF_MARGIN_X + 6, y - 1, "Sin ventas registradas.")
        y -= 14
    else:
        row_index = 0
        for idx, (name, ventas) in enumerate(top_products, start=1):
            y, page_number = ensure_space(y, 20, page_number)
            if row_index % 2 == 0:
                c.setFillColorRGB(0.98, 0.99, 1.0)
                c.rect(PDF_MARGIN_X, y - 11, PAGE_WIDTH - (2 * PDF_MARGIN_X), 13, fill=1, stroke=0)
                c.setFillColorRGB(0, 0, 0)
            medal = "1" if idx == 1 else "2" if idx == 2 else "3" if idx == 3 else str(idx)
            c.drawString(PDF_MARGIN_X + 8, y - 1, medal)
            c.drawString(PDF_MARGIN_X + 52, y - 1, name[:52])
            c.drawRightString(PAGE_WIDTH - PDF_MARGIN_X - 8, y - 1, str(int(ventas or 0)))
            y -= 14
            row_index += 1

    y -= 10
    y, page_number = ensure_space(y, 140, page_number)
    y = _draw_section_title(c, y, "Top Categorias (ingresos)")
    y = _draw_table_header(c, y, [("Categoria", 290), ("Ingresos", 110)])
    c.setFont("Helvetica", 9)
    if not top_categories:
        c.drawString(PDF_MARGIN_X + 6, y - 1, "Sin ventas registradas.")
        y -= 14
    else:
        subtotal_categories = 0.0
        row_index = 0
        for categoria, ingresos in top_categories:
            y, page_number = ensure_space(y, 20, page_number)
            if row_index % 2 == 0:
                c.setFillColorRGB(0.98, 0.99, 1.0)
                c.rect(PDF_MARGIN_X, y - 11, PAGE_WIDTH - (2 * PDF_MARGIN_X), 13, fill=1, stroke=0)
                c.setFillColorRGB(0, 0, 0)
            amount = float(ingresos or 0)
            subtotal_categories += amount
            c.drawString(PDF_MARGIN_X + 8, y - 1, (categoria or "Sin categoria")[:45])
            c.drawRightString(PAGE_WIDTH - PDF_MARGIN_X - 8, y - 1, _fmt_money(amount))
            y -= 14
            row_index += 1
        y, page_number = ensure_space(y, 20, page_number)
        c.setFillColorRGB(0.92, 0.95, 0.99)
        c.rect(PDF_MARGIN_X, y - 11, PAGE_WIDTH - (2 * PDF_MARGIN_X), 13, fill=1, stroke=0)
        c.setFillColorRGB(0.18, 0.23, 0.33)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(PDF_MARGIN_X + 8, y - 1, "Subtotal categorias")
        c.drawRightString(PAGE_WIDTH - PDF_MARGIN_X - 8, y - 1, _fmt_money(subtotal_categories))
        c.setFillColorRGB(0, 0, 0)
        c.setFont("Helvetica", 9)
        y -= 16

    y -= 6
    y, page_number = ensure_space(y, 110, page_number)
    y = _draw_section_title(c, y, "Productos de Bajo Stock (stock < 20)")
    y = _draw_table_header(c, y, [("Producto", 252), ("Categoria", 122), ("Stock", 56), ("Nivel", 72)])
    c.setFont("Helvetica", 9)
    if not low_stock_rows:
        c.drawString(PDF_MARGIN_X + 6, y - 1, "No hay productos en alerta de inventario.")
        y -= 14
    else:
        row_index = 0
        for product_name, category, stock in low_stock_rows:
            y, page_number = ensure_space(y, 20, page_number)
            if row_index % 2 == 0:
                c.setFillColorRGB(1.0, 0.98, 0.95)
                c.rect(PDF_MARGIN_X, y - 11, PAGE_WIDTH - (2 * PDF_MARGIN_X), 13, fill=1, stroke=0)
                c.setFillColorRGB(0, 0, 0)
            level = _low_stock_level(int(stock or 0))
            c.drawString(PDF_MARGIN_X + 6, y - 1, product_name[:40])
            c.drawString(PDF_MARGIN_X + 260, y - 1, (category or "Sin categoria")[:18])
            c.drawString(PDF_MARGIN_X + 386, y - 1, str(int(stock or 0)))
            if level == "CRITICO":
                c.setFillColorRGB(0.72, 0.16, 0.16)
            else:
                c.setFillColorRGB(0.75, 0.42, 0.08)
            c.drawString(PDF_MARGIN_X + 442, y - 1, level)
            c.setFillColorRGB(0, 0, 0)
            y -= 14
            row_index += 1

    y -= 8
    y, page_number = ensure_space(y, 62, page_number)
    y = _draw_section_title(c, y, "Recomendaciones")
    c.setFont("Helvetica", 9)
    c.drawString(PDF_MARGIN_X + 4, y, "- Acelerar compra para items CRITICO y revisar stock de seguridad por categoria.")
    y -= 14
    c.drawString(PDF_MARGIN_X + 4, y, "- Sostener la inversion en top productos para mantener ingresos y rotacion.")
    y -= 14
    c.drawString(PDF_MARGIN_X + 4, y, "- Monitorear ticket promedio para detectar oportunidades de cross-selling.")

    _draw_report_footer(c, "Sistema Ecommerce - Reporte gerencial", page_number)
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
