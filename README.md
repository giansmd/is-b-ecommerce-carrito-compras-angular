README.md - Sistema de Carrito de Compras Automatizado
Estructura del Proyecto

```text
.
├── backend/                # FastAPI Backend
├── frontend-angular/      # Angular Frontend
├── dashboard/             # Streamlit Dashboard
├── docker-compose.yml     # Orquestación Docker
├── railway.json           # Configuración Railway (Backend)
└── README.md
```

### Despliegue en Railway (3 Servicios Independientes)

Este proyecto está diseñado para ser desplegado como tres servicios separados en Railway desde el mismo repositorio:

1.  **Backend (FastAPI)**:
    - **Root Directory**: `backend`
    - **Variables**:
      - `DATABASE_URL`: (Generada por el plugin PostgreSQL de Railway)
      - `SECRET_KEY`: Una cadena aleatoria para JWT.
    - **Configuración**: Railway detectará automáticamente el `Dockerfile` dentro de la carpeta `backend`.

2.  **Frontend (Angular)**:
    - **Root Directory**: `frontend-angular`
    - **Variables**:
      - `BACKEND_URL`: La URL pública de tu servicio Backend (ej: `https://backend-production.up.railway.app`).
    - **Configuración**: Railway usará el `Dockerfile` multietapa (Build con Node, Serve con Nginx).

3.  **Dashboard (Streamlit)**:
    - **Root Directory**: `dashboard`
    - **Variables**:
      - `BACKEND_URL`: La URL pública de tu servicio Backend.
    - **Configuración**: Railway detectará el `Dockerfile` de Streamlit.

### Pasos para el Despliegue:

1. Crea un nuevo proyecto en Railway.
2. Agrega una base de datos PostgreSQL.
3. Agrega 3 servicios de GitHub, todos apuntando a este repositorio.
4. Para cada servicio, ve a **Settings > General > Root Directory** y asigna la carpeta correspondiente (`backend`, `frontend-angular`, o `dashboard`).
5. Configura las variables de entorno mencionadas arriba.

### Datos Iniciales (Seed)

El sistema incluye datos precargados para facilitar las pruebas. Al iniciar el backend, se crearán automáticamente:

**Usuarios:**

- **Admin**: `admin@example.com` / `admin123` (Rol: admin)
- **Vendedor**: `vendedor@example.com` / `vendedor123` (Rol: admin)
- **Cliente 1**: `cliente1@example.com` / `cliente123` (Rol: cliente)
- **Cliente 2**: `cliente2@example.com` / `cliente123` (Rol: cliente)

**Productos:**

- Laptop Gamer, Mouse Inalámbrico, Teclado Mecánico, Monitor 27' 4K, Silla Ergonómica.
- Cada producto inicial incluye `image_url` con imágenes libres alojadas en Unsplash para que el catálogo arranque con vista visual.

### Nuevas Funcionalidades

1.  **Gestión de Productos (Admin)**:
    - Los usuarios con rol `admin` pueden añadir nuevos productos.

- Los usuarios con rol `admin` pueden editar productos existentes (nombre, categoría, precio, stock, descripción e imagen).
  - Los usuarios con rol `admin` pueden eliminar productos.

2.  **Interfaz de Administración**:
    - Botón "Añadir Producto" visible solo para administradores.
    - Opciones de "Editar" y "Eliminar" en cada tarjeta de producto para administradores.

- Formulario dinámico para creación/edición.
- Campo de URL de imagen con vista previa inmediata antes de guardar.

3.  **Carrito para Cliente con Cantidades y Validación de Stock**:

- El usuario con rol `cliente` puede seleccionar cuántas unidades desea agregar por producto.
- El frontend valida en todo momento el stock disponible considerando lo que ya está en el carrito.
- Si el stock cambia, el carrito se sincroniza automáticamente para evitar cantidades inválidas.
- Antes del checkout se vuelve a validar el stock para prevenir compras con disponibilidad insuficiente.

4. **Gestión de Pedidos (Admin):**

- Se agregó una nueva página Angular para administradores: `/admin/pedidos`.
- Desde la pantalla principal, un admin puede entrar con el botón **"Ver pedidos"**.
- La página muestra:
  - listado de pedidos (id, cliente, fecha, estado, total, cantidad de items),
  - detalle por pedido (productos, cantidad, precio unitario, subtotal y total final).
- Si un usuario no autenticado o no admin intenta entrar, se redirige a la tienda principal.

### Endpoints nuevos (Pedidos Admin)

Estos endpoints requieren JWT válido de un usuario con rol `admin` en el header `Authorization: Bearer <token>`.

#### `GET /api/orders/admin`

Lista todos los pedidos ordenados por fecha descendente.

Ejemplo de respuesta:

```json
[
  {
    "id": 12,
    "user_id": 3,
    "customer_email": "cliente1@example.com",
    "total_amount": 540.5,
    "status": "completado",
    "order_date": "2026-04-27T14:33:10.123456",
    "items_count": 2
  }
]
```

#### `GET /api/orders/admin/{order_id}`

Devuelve el detalle completo de un pedido.

Ejemplo de respuesta:

```json
{
  "id": 12,
  "user_id": 3,
  "customer_email": "cliente1@example.com",
  "total_amount": 540.5,
  "status": "completado",
  "order_date": "2026-04-27T14:33:10.123456",
  "items": [
    {
      "id": 44,
      "product_id": 1,
      "product_name": "Laptop Gamer",
      "quantity": 1,
      "price": 500,
      "subtotal": 500
    }
  ]
}
```

### Frontend: nueva página de pedidos

Archivos agregados:

- `frontend-angular/src/app/orders-admin/orders-admin.component.ts`
- `frontend-angular/src/app/orders-admin/orders-admin.component.html`
- `frontend-angular/src/app/orders-admin/orders-admin.component.css`
- `frontend-angular/src/app/services/order.service.ts`

Cambios de navegación:

- Nueva ruta Angular: `admin/pedidos`
- La pantalla principal de tienda se movió a `StoreComponent` (`/`)
- `AppComponent` ahora actúa como shell con `router-outlet`

### Ejecución Local con Docker

```bash
docker-compose up --build
```

### Perfiles Docker Compose (Dev y Prod)

Se agregaron dos archivos para separar flujos de trabajo:

- `docker-compose.dev.yml`: entorno de desarrollo con recarga en caliente.
  - Backend con `uvicorn --reload`.
  - Frontend Angular con `ng serve` (puerto `4200`).
  - Dashboard y backend montando código local como volumen.
- `docker-compose.prod.yml`: entorno orientado a ejecución tipo producción.
  - Usa los Dockerfiles de cada servicio.
  - Frontend servido con Nginx (puerto `4200 -> 80`).

Comandos:

```bash
# Desarrollo
docker compose -f docker-compose.dev.yml up --build

# Producción (local)
docker compose -f docker-compose.prod.yml up --build -d
```

- Angular: http://localhost:4200
- Dashboard: http://localhost:8501
- Backend API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs

### Variables de Entorno

**Backend (FastAPI)**

- `DATABASE_URL`: DSN de PostgreSQL. En Docker Compose se usa `postgresql+asyncpg://postgres:password@postgres:5432/shopping_db`.
- `SECRET_KEY`: clave para JWT.

**Frontend (Angular)**

- `BACKEND_URL`: URL pública del backend.
  - En Docker, el contenedor escribe `assets/env.js` al iniciar (ver `frontend-angular/entrypoint.sh`).
  - En el navegador, `AuthService` lee `window.env.BACKEND_URL` y, si no existe, usa `http://localhost:8000`.

**Dashboard (Streamlit)**

- `BACKEND_URL`: URL interna para llamadas API desde Streamlit.
  - En Docker Compose para el servicio `dashboard`, usar `http://backend:8000` (DNS interno de Docker).
- `BACKEND_PUBLIC_URL`: URL pública usada para enlaces que abre el navegador (por ejemplo, PDFs).
  - Valor recomendado en local con Docker Compose: `http://localhost:8000`.

### Reportes y Métricas

**Reportes PDF**

- Se generan en el backend y quedan disponibles como archivos estáticos bajo `/reports`.
- Ejemplo: si el endpoint devuelve `{"pdf_url":"/reports/management_xxx.pdf"}`, se abre en `http://localhost:8000/reports/management_xxx.pdf`.

**Métricas (Dashboard)**

- `GET /api/stats/daily-sales`: devuelve pedidos de hoy, ingresos de hoy e ingresos acumulados.
- `GET /api/stats/top-products`: top por unidades vendidas (usa `order_details` + `products`).
- `GET /api/stats/category-sales`: distribución por categoría (ingresos y unidades).
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
image_url VARCHAR(500),
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
Request: {"name":"Producto B","price":150,"category":"Ropa","stock":50,"image_url":"https://..."}
Response: {"id":2,"message":"Producto creado"}

PUT /api/products/{product_id} (Admin only)
Request: {"price":200,"stock":40,"image_url":"https://..."}
Response: {"id":2,"name":"Producto B","price":200,"stock":40}

DELETE /api/products/{product_id} (Admin only)
Response: {"message":"Producto eliminado"}
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
Response: {"total_ventas_hoy":3,"ingresos_hoy":120.50,"ingresos_totales":50000.00}

GET /api/stats/top-products
Response: [{"producto":"Laptop Gamer","ventas":12},{"producto":"Mouse Inalámbrico","ventas":9}]

GET /api/stats/user-metrics
Response: {"promedio_compra_usuario":250,"frecuencia_compras":2.5}
GET /api/stats/category-sales
Response: [{"categoria":"Electronica","ventas":12,"ingresos":1234.50}]

Código fuente (referencias)

- Backend (FastAPI): backend/main.py
- Modelos SQLAlchemy: backend/models.py
- Esquemas Pydantic: backend/schemas.py
- Inicialización/seed: backend/init_db.py (opcional; también hay seed en startup)
- Frontend Angular: frontend-angular/src/app/app.component.(ts|html) y frontend-angular/src/app/services/\*.ts
- Dashboard Streamlit: dashboard/app.py
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
  ports: - "5433:5432"
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

ADMIN_EMAIL=admin@mail.com ADMIN_PASSWORD=changeme docker-compose exec backend python init_db.py
Configuración Manual (sin Docker)
bash

# Backend

cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Angular

cd frontend-angular
npm install
ng serve --port 4200

# Streamlit

cd dashboard
pip install streamlit requests pandas plotly
streamlit run app.py --port 8501
Notas Importantes
JWT tokens expiran en 24 horas

Solo administradores pueden crear/editar productos

Reportes PDF se guardan en carpeta /reports

Para producción, usar variables de entorno y HTTPS
