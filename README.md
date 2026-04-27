README.md - Sistema de Carrito de Compras Automatizado
Estructura del Proyecto

```text
.
├── backend/                # FastAPI Backend
│   ├── Dockerfile
│   ├── main.py
│   ├── models.py
│   ├── schemas.py
│   ├── database.py
│   ├── init_db.py
│   └── requirements.txt
├── frontend-angular/      # Angular Frontend (Por implementar)
├── dashboard/             # Streamlit Dashboard (Por implementar)
├── docker-compose.yml     # Orquestación Docker
├── railway.json           # Configuración Railway
└── README.md
```

Arquitectura del Sistema
text
┌─────────────────────────────────────────────────────────────┐
│ CLIENTE │
├──────────────────┬──────────────────┬───────────────────────┤
│ Angular App │ Streamlit App │ │
│ (Puerto:4200) │ (Puerto:8501) │ │
└────────┬─────────┴────────┬─────────┘ │
│ │ │
└──────────┬───────┘ │
│ │
┌──────────▼──────────┐ │
│ FastAPI Backend │ │
│ (Puerto:8000) │ │
└──────────┬──────────┘ │
│ │
┌──────────▼──────────┐ │
│ PostgreSQL │ │
│ (Puerto:5432) │ │
└─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
Flujo de Datos:

Usuario interactúa con Angular (gestión usuarios/carrito) o Streamlit (dashboard)

Frontend envía peticiones REST a FastAPI

FastAPI procesa lógica de negocio y consulta PostgreSQL

Respuesta retorna al frontend correspondiente

Reportes PDF generados en backend, descargados desde Angular

Base de Datos (PostgreSQL)
sql
-- Tabla de Usuarios
CREATE TABLE users (
id SERIAL PRIMARY KEY,
email VARCHAR(255) UNIQUE NOT NULL,
password_hash VARCHAR(255) NOT NULL,
role VARCHAR(50) DEFAULT 'cliente', -- 'cliente' o 'admin'
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de Productos
CREATE TABLE products (
id SERIAL PRIMARY KEY,
name VARCHAR(255) NOT NULL,
description TEXT,
price DECIMAL(10,2) NOT NULL,
category VARCHAR(100),
stock INT DEFAULT 0,
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de Carritos
CREATE TABLE carts (
id SERIAL PRIMARY KEY,
user_id INT REFERENCES users(id),
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
status VARCHAR(50) DEFAULT 'activo' -- 'activo', 'procesado'
);

-- Tabla de Items del Carrito
CREATE TABLE cart_items (
id SERIAL PRIMARY KEY,
cart_id INT REFERENCES carts(id),
product_id INT REFERENCES products(id),
quantity INT NOT NULL,
price_at_time DECIMAL(10,2) NOT NULL
);

-- Tabla de Pedidos
CREATE TABLE orders (
id SERIAL PRIMARY KEY,
user_id INT REFERENCES users(id),
total_amount DECIMAL(10,2) NOT NULL,
order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
status VARCHAR(50) DEFAULT 'completado'
);

-- Tabla de Detalles de Pedido
CREATE TABLE order_details (
id SERIAL PRIMARY KEY,
order_id INT REFERENCES orders(id),
product_id INT REFERENCES products(id),
quantity INT NOT NULL,
price DECIMAL(10,2) NOT NULL
);
Endpoints Backend (FastAPI)
Autenticación
http
POST /api/auth/register
Request: {"email": "user@mail.com", "password": "123456", "role": "cliente"}
Response: {"user_id": 1, "message": "Usuario registrado"}

POST /api/auth/login
Request: {"email": "user@mail.com", "password": "123456"}
Response: {"access_token": "jwt_token", "role": "cliente"}
Productos (CRUD)
http
GET /api/products
Response: [{"id":1,"name":"Producto A","price":100,"category":"Electrónica"}]

POST /api/products (Admin only)
Request: {"name":"Producto B","price":150,"category":"Ropa","stock":50}
Response: {"id":2,"message":"Producto creado"}
Carrito
http
POST /api/cart/add
Request: {"user_id":1,"product_id":1,"quantity":2}
Response: {"cart_id":1,"message":"Producto agregado"}

DELETE /api/cart/remove/{item_id}
Response: {"message":"Producto eliminado"}

POST /api/cart/checkout
Request: {"user_id":1}
Response: {"order_id":1,"total":200,"message":"Compra realizada"}
Reportes PDF
http
POST /api/reports/operational
Request: {"start_date":"2024-01-01","end_date":"2024-01-31"}
Response: {"pdf_url":"/reports/operational_123.pdf"}

POST /api/reports/management
Request: {}
Response: {"pdf_url":"/reports/management_456.pdf"}
Estadísticas Dashboard
http
GET /api/stats/daily-sales
Response: {"total_ventas_hoy":1500,"ingresos_totales":50000}

GET /api/stats/top-products
Response: [{"producto":"A","ventas":50},{"producto":"B","ventas":30}]

GET /api/stats/user-metrics
Response: {"promedio_compra_usuario":250,"frecuencia_compras":2.5}
Fragmentos de Código
Backend - main.py (FastAPI)
python
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer
import asyncpg
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

app = FastAPI()
security = HTTPBearer()

# Conexión BD

async def get_db():
conn = await asyncpg.connect(
host="localhost", database="shopping_db",
user="postgres", password="password"
)
return conn

# Endpoint: Agregar al carrito

@app.post("/api/cart/add")
async def add_to_cart(user_id: int, product_id: int, quantity: int, db=Depends(get_db)): # Verificar stock
product = await db.fetchrow("SELECT price, stock FROM products WHERE id = $1", product_id)
if not product:
raise HTTPException(404, "Producto no existe")
if product['stock'] < quantity:
raise HTTPException(400, "Stock insuficiente")

    # Obtener o crear carrito activo
    cart = await db.fetchrow("SELECT id FROM carts WHERE user_id = $1 AND status = 'activo'", user_id)
    if not cart:
        cart = await db.fetchrow("INSERT INTO carts (user_id) VALUES ($1) RETURNING id", user_id)

    # Agregar item
    await db.execute("""
        INSERT INTO cart_items (cart_id, product_id, quantity, price_at_time)
        VALUES ($1, $2, $3, $4)
    """, cart['id'], product_id, quantity, product['price'])

    return {"message": "Producto agregado al carrito"}

# Generar reporte PDF

@app.post("/api/reports/operational")
async def generate_operational_report(start_date: str, end_date: str, db=Depends(get_db)):
orders = await db.fetch("""
SELECT o.id, u.email, o.total_amount, o.order_date
FROM orders o JOIN users u ON o.user_id = u.id
WHERE o.order_date BETWEEN $1 AND $2
""", start_date, end_date)

    pdf_path = f"reports/operational_{start_date}_{end_date}.pdf"
    c = canvas.Canvas(pdf_path, pagesize=letter)
    c.drawString(100, 750, f"Reporte de Pedidos: {start_date} a {end_date}")
    y = 700
    for order in orders:
        c.drawString(100, y, f"Pedido #{order['id']} - {order['email']} - ${order['total_amount']}")
        y -= 20
    c.save()
    return {"pdf_url": f"/{pdf_path}"}

Frontend Angular - cart.service.ts
typescript
import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';

@Injectable({providedIn: 'root'})
export class CartService {
private apiUrl = 'http://localhost:8000/api';

constructor(private http: HttpClient) {}

addToCart(productId: number, quantity: number, token: string) {
const headers = new HttpHeaders().set('Authorization', `Bearer ${token}`);
return this.http.post(`${this.apiUrl}/cart/add`,
{ user_id: 1, product_id: productId, quantity },
{ headers });
}

checkout(token: string) {
return this.http.post(`${this.apiUrl}/cart/checkout`,
{ user_id: 1 },
{ headers: new HttpHeaders().set('Authorization', `Bearer ${token}`) });
}

downloadReport(startDate: string, endDate: string, type: string, token: string) {
const url = `${this.apiUrl}/reports/${type}`;
return this.http.post(url, { start_date: startDate, end_date: endDate },
{ responseType: 'blob', headers: new HttpHeaders().set('Authorization', `Bearer ${token}`) });
}
}
Dashboard Streamlit - dashboard.py
python
import streamlit as st
import requests
import pandas as pd
import plotly.express as px

API_URL = "http://localhost:8000/api"

st.set_page_config(page_title="Dashboard Ventas", layout="wide")
st.title("📊 Dashboard de Métricas")

# Obtener métricas

daily = requests.get(f"{API_URL}/stats/daily-sales").json()
st.metric("Ventas del día", f"${daily['total_ventas_hoy']}")
st.metric("Ingresos totales", f"${daily['ingresos_totales']}")

# Gráfico: Productos más vendidos

top_products = requests.get(f"{API_URL}/stats/top-products").json()
df = pd.DataFrame(top_products)
fig = px.bar(df, x='producto', y='ventas', title='Productos Más Vendidos')
st.plotly_chart(fig)

# Estadísticas usuarios

user_stats = requests.get(f"{API_URL}/stats/user-metrics").json()
col1, col2 = st.columns(2)
col1.metric("Promedio compra/usuario", f"${user_stats['promedio_compra_usuario']}")
col2.metric("Frecuencia compras/mes", f"{user_stats['frecuencia_compras']} veces")
Configuración y Despliegue
Docker Compose (docker-compose.yml)
yaml
version: '3.8'
services:
postgres:
image: postgres:15
environment:
POSTGRES_DB: shopping_db
POSTGRES_USER: postgres
POSTGRES_PASSWORD: password
ports: - "5432:5432"
volumes: - postgres_data:/var/lib/postgresql/data

backend:
build: ./backend
ports: - "8000:8000"
depends_on: - postgres
environment:
DATABASE_URL: postgresql://postgres:password@postgres/shopping_db

angular:
build: ./frontend-angular
ports: - "4200:80"
depends_on: - backend

streamlit:
build: ./dashboard
ports: - "8501:8501"
depends_on: - backend

volumes:
postgres_data:
Despliegue en Railway

```bash
# 1. Instalar Railway CLI y loguearse
npm i -g @railway/cli
railway login

# 2. Vincular el proyecto
railway link

# 3. Desplegar
railway up
```

Instrucciones Rápidas
bash

# 1. Clonar repositorio

git clone <repo-url>
cd shopping-cart-system

# 2. Levantar con Docker

docker-compose up -d

# 3. Acceder a aplicaciones

# Angular: http://localhost:4200

# Streamlit: http://localhost:8501

# API Docs: http://localhost:8000/docs

# 4. Crear admin inicial (ejecutar en backend)

docker-compose exec backend python init_db.py
Configuración Manual (sin Docker)
bash

# Backend

cd backend
pip install fastapi uvicorn asyncpg reportlab python-multipart
uvicorn main:app --reload --port 8000

# Angular

cd frontend-angular
npm install
ng serve --port 4200

# Streamlit

cd dashboard
pip install streamlit requests pandas plotly
streamlit run dashboard.py --port 8501
Notas Importantes
JWT tokens expiran en 24 horas

Solo administradores pueden crear/editar productos

Reportes PDF se guardan en carpeta /reports

Para producción, usar variables de entorno y HTTPS
