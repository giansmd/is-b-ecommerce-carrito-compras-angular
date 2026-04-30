**Paso a paso (Railway + este repo monorepo)**\
Estructura detectada: `backend/` (FastAPI + Postgres), `dashboard/` (Streamlit), `frontend-angular/` (Angular servido por Nginx) y un servicio de **BD** (Postgres) en Railway.

***

## 1) Proyecto y BD (Postgres)

1. Crea (o usa) un proyecto en Railway.
2. Agrega la BD desde el canvas (“Add Database → Postgres”) o por CLI:
   ```powershell
   railway add --database postgres
   ```
   (Comando `add` documentado en CLI: <https://docs.railway.com/guides/cli>)

***

## 2) Crea los 3 servicios de app en Railway

Crea 3 servicios vacíos dentro del mismo proyecto (nombres recomendados para que los “references” funcionen igual):

```powershell
railway add --service backend
railway add --service dashboard
railway add --service frontend-angular
```

(“Create a service” vía `railway add --service …`: <https://docs.railway.com/guides/cli>)

***

## 3) Configura variables (la parte clave)

Railway permite referenciar variables de otro servicio con `${{SERVICE_NAME.VAR}}` (docs: <https://docs.railway.com/guides/variables>).

### 3.1 Backend

Este backend lee `DATABASE_URL`, `SECRET_KEY`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`.

En PowerShell, pon los `KEY=value` entre comillas simples para que no intente expandir `$...`:

```powershell
railway variable set `
  'DATABASE_URL=${{Postgres.DATABASE_URL}}' `
  'SECRET_KEY=pon-un-secreto-largo' `
  'STRIPE_SECRET_KEY=sk_...' `
  'STRIPE_WEBHOOK_SECRET=whsec_...' `
  --service backend
```

### 3.2 Publica dominio del backend (necesario para el navegador)

Genera un dominio público para `backend`:

```powershell
railway domain --service backend
```

(Docs `railway domain`: <https://docs.railway.com/cli/domain>)

### 3.3 Dashboard (Streamlit) → conecta al backend por red privada + links públicos

- Tráfico **servicio→servicio**: usa red privada (`*.railway.internal`) (docs: <https://docs.railway.com/guides/private-networking>)
- Links a PDFs desde el navegador: usa dominio público del backend.

```powershell
railway variable set `
  'BACKEND_URL=http://${{backend.RAILWAY_PRIVATE_DOMAIN}}:8000' `
  'BACKEND_PUBLIC_URL=https://${{backend.RAILWAY_PUBLIC_DOMAIN}}' `
  --service dashboard
```

### 3.4 Frontend Angular (Nginx) → backend público

El Angular del repo toma `window.env.BACKEND_URL`, y el Dockerfile lo inyecta desde la variable `BACKEND_URL` en runtime.

```powershell
railway variable set `
  'BACKEND_URL=https://${{backend.RAILWAY_PUBLIC_DOMAIN}}' `
  --service frontend-angular
```

***

## 4) Deploys desde este repo (CLI)

Railway CLI permite deployar una subcarpeta con `railway up [PATH]` (docs: <https://docs.railway.com/cli/up>).\
Para monorepos, usa `--path-as-root` para que esa carpeta sea el “root” del build (docs: <https://docs.railway.com/cli/deploying>).

Desde la raíz del repo:

```powershell
cd c:\Users\gian_\dev\unt\software-1\semana-02\is-b-ecommerce-carrito-compras-angular
railway link
```

Luego, deploy de cada servicio apuntando a su carpeta:

```powershell
railway up .\backend --service backend --path-as-root
railway up .\dashboard --service dashboard --path-as-root
railway up .\frontend-angular --service frontend-angular --path-as-root
```

Opcional (si no quieres quedarte pegado a logs): agrega `--detach`:

```powershell
railway up .\backend --service backend --path-as-root --detach
```

***

## 5) Dominios públicos para dashboard y frontend

Si quieres exponerlos al público:

```powershell
railway domain --service dashboard
railway domain --service frontend-angular
```

***

### Nota importante sobre “ports”

- En Railway, el “routing” público depende de que el servicio escuche en el puerto correcto (variable `PORT` / configuración de networking). Si alguno queda en “Deploy OK pero no responde”, revisa en Settings del servicio el puerto que Railway está ruteando vs el que escucha el contenedor (backend=8000, dashboard=8501, frontend=80) y ajústalo ahí. (Contexto de `PORT` en networking: <https://docs.railway.com/networking/public-networking>)

Con esto quedan 4 servicios: **Postgres + backend + dashboard + frontend-angular**, y los deploys los haces con los `railway up` de arriba.
