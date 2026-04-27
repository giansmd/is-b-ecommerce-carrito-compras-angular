import asyncio
import os
from database import engine, Base, AsyncSessionLocal
from models import User, Product, Cart, CartItem, Order, OrderDetail
from sqlalchemy import select, update, text
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

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

async def init_db():
    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS image_url VARCHAR(500)"))
    
    print("Database tables created successfully")
    
    async with AsyncSessionLocal() as session:
        seed_users = [
            {"email": "admin@example.com", "password": "admin123", "role": "admin"},
            {"email": "cliente1@example.com", "password": "cliente123", "role": "cliente"},
            {"email": "cliente2@example.com", "password": "cliente123", "role": "cliente"},
            {"email": "vendedor@example.com", "password": "vendedor123", "role": "admin"},
        ]
        seed_emails = [user["email"] for user in seed_users]
        result = await session.execute(select(User.email).where(User.email.in_(seed_emails)))
        existing_emails = set(result.scalars().all())

        missing_users = [
            User(
                email=user["email"],
                password_hash=pwd_context.hash(user["password"]),
                role=user["role"],
            )
            for user in seed_users
            if user["email"] not in existing_emails
        ]
        if missing_users:
            print(f"Populating missing users... ({len(missing_users)} new)")
            session.add_all(missing_users)
            await session.commit()
            print("Users populated successfully")

        # Check if products exist
        result = await session.execute(select(Product))
        if not result.scalars().first():
            print("Populating initial products...")
            products = [Product(**product_data) for product_data in DEFAULT_PRODUCTS]
            session.add_all(products)
            await session.commit()
            print("Products populated successfully")
        else:
            for product_data in DEFAULT_PRODUCTS:
                await session.execute(
                    update(Product)
                    .where(Product.name == product_data["name"], Product.image_url.is_(None))
                    .values(image_url=product_data["image_url"])
                )
            await session.commit()

if __name__ == "__main__":
    asyncio.run(init_db())
