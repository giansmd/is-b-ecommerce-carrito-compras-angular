# Manual de Usuario — Sistema E‑Commerce (Carrito + Pagos + Administración)

Este documento explica cómo usar las interfaces del proyecto (Tienda Angular, Administración y Dashboard de métricas) desde la perspectiva de usuario final.

## Acceso rápido (local)

- Tienda (Frontend Angular): http://localhost:4200
- API (FastAPI): http://localhost:8000
- Documentación API (Swagger): http://localhost:8000/docs
- Dashboard (Streamlit): http://localhost:8501

Para levantar todo en local con Docker:

```bash
docker-compose up --build
```

## Roles del sistema

El sistema maneja dos roles principales:

- **cliente**: navega el catálogo, agrega productos al carrito e inicia el flujo de pago.
- **admin**: gestiona productos, genera reportes y puede ver pedidos.

## Usuarios de prueba (seed)

Al iniciar el backend se cargan usuarios y productos de ejemplo:

- Admin: `admin@example.com` / `admin123`
- Vendedor: `vendedor@example.com` / `vendedor123` (rol admin)
- Cliente 1: `cliente1@example.com` / `cliente123`
- Cliente 2: `cliente2@example.com` / `cliente123`

## Tienda (Angular)

### 1) Iniciar sesión

1. Entra a http://localhost:4200.
2. En el formulario **Login**, escribe tu email y password.
3. Pulsa **Ingresar**.
4. En la barra superior aparecerá tu correo y el botón **Cerrar Sesión**.

Notas:

- Si el login falla, se mostrará un mensaje de error.
- Si inicias sesión como **admin**, verás herramientas de administración y no podrás agregar productos al carrito.

### 2) Navegar productos (catálogo)

En la sección **Nuestros Productos** se listan tarjetas con:

- nombre, categoría y descripción,
- precio,
- stock disponible,
- imagen (si el producto tiene URL de imagen).

### 3) Agregar productos al carrito (solo cliente)

1. En la tarjeta del producto, usa el selector de cantidad (botones `-` y `+` o el input numérico).
2. Revisa el indicador **Disponible para agregar** (considera lo que ya tienes en el carrito).
3. Pulsa **Añadir al Carrito**.

Validaciones importantes:

- Si el stock disponible llega a 0, el botón se deshabilita.
- Si el stock cambió en el servidor, el sistema vuelve a cargar productos y ajusta el carrito.

Cómo ajustar cantidades:

- Para **aumentar** unidades de un producto ya agregado, vuelve a agregar el mismo producto con la cantidad deseada.
- La interfaz actual no incluye botones para disminuir cantidades o eliminar ítems desde el carrito.

### 4) Revisar carrito

En el panel derecho se muestra:

- total de ítems (**Carrito (N)**),
- lista de productos con `cantidad x precio`,
- total acumulado.

### 5) Ir a pago (Stripe)

1. Con al menos un producto en el carrito, pulsa **Ir a pago con Stripe**.
2. Se abrirá la página **Resumen de pago** (`/payment`) con el detalle de ítems y el total.
3. Pulsa **Pagar con Stripe** para que el sistema cree una sesión de pago y te redirija a la página de pago de Stripe.

Notas:

- Para que el pago funcione, el backend debe tener configurada la variable `STRIPE_SECRET_KEY`.
- Al completar el pago, Stripe redirige de vuelta a `/payment` con parámetros de estado. La app no muestra una pantalla de confirmación detallada; el pedido se registra en el backend cuando llega el webhook de Stripe.

## Funciones de Administrador (Angular)

### 1) Gestión de productos

Al iniciar sesión con rol **admin**, en la parte superior del catálogo aparecen:

- **Añadir Producto**
- Opciones **Editar** y **Eliminar** en cada tarjeta

Crear producto:

1. Pulsa **Añadir Producto**.
2. Completa el formulario (nombre, categoría, precio, stock, descripción y URL de imagen).
3. Verifica la vista previa de imagen (si cargaste una URL).
4. Pulsa **Guardar**.

Editar producto:

1. En la tarjeta del producto, pulsa **Editar**.
2. Modifica los campos necesarios.
3. Pulsa **Guardar**.

Eliminar producto:

1. En la tarjeta del producto, pulsa **Eliminar**.
2. Confirma la acción en el diálogo.

### 2) Ver pedidos (Admin)

1. En la tienda, pulsa **Ver pedidos**.
2. Se abrirá la ruta `/admin/pedidos`.
3. En el panel izquierdo verás el listado de pedidos.
4. Haz clic en un pedido para ver su detalle (productos, cantidades, subtotales y total).
5. Usa **Volver a tienda** para regresar.

Si un usuario no autenticado o no admin intenta ingresar a esta ruta, será redirigido a la tienda.

### 3) Reportes PDF (Admin)

En el panel derecho de la tienda (debajo del carrito), un admin puede:

- elegir **Inicio** y **Fin** (rango de fechas),
- generar **Reporte Operacional**,
- generar **Reporte Gerencial**.

Al generarse, el reporte se abre en una pestaña nueva del navegador.

## Dashboard (Streamlit)

Acceso: http://localhost:8501

El dashboard está pensado para visualizar métricas y generar reportes desde una interfaz dedicada.

### Funcionalidades

- **Métricas del día**: pedidos de hoy, ingresos de hoy, ingresos totales, promedio de compra.
- **Top productos**: gráfico de barras con unidades vendidas.
- **Distribución por categoría**: gráfico circular con ingresos por categoría.
- **Reportes PDF**: generación operacional (con rango de fechas) y gerencial.

Notas:

- El dashboard consume datos desde el backend. Si el backend no está disponible, mostrará errores de conexión.
- Los links de reportes abren PDFs alojados por el backend bajo `/reports`.

## Problemas comunes

- **No carga la tienda / error de API**: verifica que el backend esté arriba en http://localhost:8000.
- **No puedo iniciar sesión**: usa las credenciales de seed y revisa que la base inicial se haya creado.
- **No se abre el PDF de reportes**: desactiva el bloqueo de pop-ups o abre el link manualmente.
- **Pago con Stripe falla**: configura `STRIPE_SECRET_KEY` en el backend; sin esa variable, el backend rechaza la creación de sesión.
