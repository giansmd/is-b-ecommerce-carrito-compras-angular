from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime
from decimal import Decimal

class UserBase(BaseModel):
    email: EmailStr
    role: Optional[str] = "cliente"

class UserCreate(UserBase):
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    role: str
    created_at: datetime
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str

class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: Decimal
    category: Optional[str] = None
    stock: int
    image_url: Optional[str] = None

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = None
    category: Optional[str] = None
    stock: Optional[int] = None
    image_url: Optional[str] = None

class ProductResponse(ProductBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True

class CartItemAdd(BaseModel):
    user_id: int
    product_id: int
    quantity: int

class OrderResponse(BaseModel):
    id: int
    total_amount: Decimal
    order_date: datetime
    status: str
    class Config:
        from_attributes = True

class OrderAdminListItem(BaseModel):
    id: int
    user_id: int
    customer_email: str
    total_amount: Decimal
    status: str
    order_date: datetime
    items_count: int

class OrderAdminDetailItem(BaseModel):
    id: int
    product_id: int
    product_name: str
    quantity: int
    price: Decimal
    subtotal: Decimal

class OrderAdminDetail(BaseModel):
    id: int
    user_id: int
    customer_email: str
    total_amount: Decimal
    status: str
    order_date: datetime
    items: List[OrderAdminDetailItem]

class ReportRequest(BaseModel):
    start_date: str
    end_date: str
