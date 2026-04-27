import asyncio
import os
from database import engine, Base, AsyncSessionLocal
from models import User, Product, Cart, CartItem, Order, OrderDetail
from sqlalchemy import select
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def init_db():
    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
    
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
            products = [
                Product(name="Laptop Gamer", description="Laptop de alto rendimiento", price=1500.00, category="Electronica", stock=10),
                Product(name="Mouse Inalámbrico", description="Mouse ergonómico", price=25.50, category="Accesorios", stock=50),
                Product(name="Teclado Mecánico", description="Teclado RGB switch blue", price=80.00, category="Accesorios", stock=20),
                Product(name="Monitor 27' 4K", description="Monitor ultra HD", price=450.00, category="Electronica", stock=15),
                Product(name="Silla Ergonómica", description="Silla para oficina", price=200.00, category="Muebles", stock=5),
            ]
            session.add_all(products)
            await session.commit()
            print("Products populated successfully")

if __name__ == "__main__":
    asyncio.run(init_db())
