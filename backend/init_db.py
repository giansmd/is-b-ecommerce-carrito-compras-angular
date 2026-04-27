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
    admin_email = os.getenv("ADMIN_EMAIL")
    admin_password = os.getenv("ADMIN_PASSWORD")
    if admin_email and admin_password:
        async with AsyncSessionLocal() as session:
            existing = await session.execute(select(User).where(User.email == admin_email))
            if not existing.scalar_one_or_none():
                admin = User(
                    email=admin_email,
                    password_hash=pwd_context.hash(admin_password),
                    role="admin",
                )
                session.add(admin)
                await session.commit()
                print(f"Admin created: {admin_email}")

if __name__ == "__main__":
    asyncio.run(init_db())
