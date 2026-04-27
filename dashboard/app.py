import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import os
from typing import Optional

# Configuración
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
BACKEND_PUBLIC_URL = os.getenv("BACKEND_PUBLIC_URL", "http://localhost:8000").rstrip("/")


def build_backend_candidates() -> list[str]:
    primary = BACKEND_URL.rstrip("/")
    candidates = [primary]
    for url in ["http://backend:8000", "http://host.docker.internal:8000", "http://localhost:8000"]:
        normalized = url.rstrip("/")
        if normalized not in candidates:
            candidates.append(normalized)
    return candidates


BACKEND_CANDIDATES = build_backend_candidates()


def api_request(path: str, method: str = "GET", json: Optional[dict] = None, timeout: int = 20):
    last_error = None
    for base_url in BACKEND_CANDIDATES:
        try:
            response = requests.request(method, f"{base_url}{path}", json=json, timeout=timeout)
            return response, base_url, None
        except requests.RequestException as exc:
            last_error = exc
    return None, None, last_error

st.set_page_config(page_title="Dashboard de Ventas - E-commerce", layout="wide")

st.markdown(
    """
<style>
  .block-container { padding-top: 2.25rem; padding-bottom: 2.25rem; }
  [data-testid="stMetricValue"] { letter-spacing: -0.02em; }
  [data-testid="stSidebar"] { background: linear-gradient(180deg, rgba(13,110,253,0.10), rgba(13,110,253,0.00)); }
  .stButton>button { border-radius: 10px; padding: 0.55rem 0.85rem; }
</style>
""",
    unsafe_allow_html=True,
)

st.title("📊 Dashboard de Gestión de Ventas")

today = pd.Timestamp.utcnow().date()
default_end = today
default_start = (pd.Timestamp(today) - pd.Timedelta(days=7)).date()

# Sidebar para filtros y acciones
st.sidebar.header("Acciones")

st.sidebar.subheader("Reportes")
range_start = st.sidebar.date_input("Inicio", value=default_start)
range_end = st.sidebar.date_input("Fin", value=default_end)

if st.sidebar.button("Generar Reporte Operacional"):
    payload = {"start_date": str(range_start), "end_date": str(range_end)}
    response, used_base_url, error = api_request(
        "/api/reports/operational", method="POST", json=payload, timeout=30
    )
    if response is None:
        st.sidebar.error(f"Error de conexión: {error}")
    elif response.status_code == 200:
        pdf_url = response.json()["pdf_url"]
        st.sidebar.success("Reporte generado")
        st.sidebar.markdown(f"[Abrir reporte]({BACKEND_PUBLIC_URL}{pdf_url})")
    else:
        st.sidebar.error(response.json().get("detail", "Error al generar reporte"))

if st.sidebar.button("Generar Reporte Gerencial"):
    response, used_base_url, error = api_request("/api/reports/management", method="POST", timeout=30)
    if response is None:
        st.sidebar.error(f"Error de conexión: {error}")
    elif response.status_code == 200:
        pdf_url = response.json()["pdf_url"]
        st.sidebar.success("Reporte generado")
        st.sidebar.markdown(f"[Abrir reporte]({BACKEND_PUBLIC_URL}{pdf_url})")
    else:
        st.sidebar.error("Error al generar reporte")

# Métricas Principales
st.subheader("📈 Métricas del Día")
col1, col2, col3, col4 = st.columns(4)

sales_res, _, sales_error = api_request("/api/stats/daily-sales", timeout=20)
if sales_res is None:
    st.error(f"No se pudieron cargar las métricas: {sales_error}")
elif sales_res.status_code == 200:
    sales_data = sales_res.json()
    col1.metric("Pedidos Hoy", f"{sales_data['total_ventas_hoy']}")
    col2.metric("Ingresos Hoy", f"${sales_data.get('ingresos_hoy', 0):,.2f}")
    col3.metric("Ingresos Totales", f"${sales_data['ingresos_totales']:,.2f}")

user_res, _, user_error = api_request("/api/stats/user-metrics", timeout=20)
if user_res is None:
    st.error(f"No se pudieron cargar las métricas de usuarios: {user_error}")
elif user_res.status_code == 200:
    user_data = user_res.json()
    col4.metric("Promedio de Compra", f"${user_data['promedio_compra_usuario']:,.2f}")

# Gráficos
st.divider()
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Top Productos más Vendidos")
    top_res, _, top_error = api_request("/api/stats/top-products", timeout=20)
    if top_res is None:
        st.error(f"Error al cargar top productos: {top_error}")
    elif top_res.status_code == 200:
        top_data = top_res.json()
        df_top = pd.DataFrame(top_data)
        fig = px.bar(df_top, x="producto", y="ventas", color="producto", title="Unidades vendidas por producto")
        st.plotly_chart(fig, use_container_width=True)

with col_right:
    st.subheader("Distribución de Categorías")
    cat_res, _, cat_error = api_request("/api/stats/category-sales", timeout=20)
    if cat_res is None:
        st.error(f"Error al cargar categorías: {cat_error}")
    elif cat_res.status_code == 200:
        cat_data = cat_res.json()
        df_cat = pd.DataFrame(cat_data)
        if not df_cat.empty:
            fig_pie = px.pie(df_cat, values="ingresos", names="categoria", title="Ingresos por Categoría")
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("Aún no hay ventas por categoría.")
    else:
        st.error("No se pudo cargar la distribución de categorías.")

st.divider()
st.info("Este dashboard consume datos en tiempo real desde la API de FastAPI.")
