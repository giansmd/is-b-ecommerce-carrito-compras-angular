import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import os

# Configuración
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

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
    try:
        payload = {"start_date": str(range_start), "end_date": str(range_end)}
        response = requests.post(f"{BACKEND_URL}/api/reports/operational", json=payload, timeout=30)
        if response.status_code == 200:
            pdf_url = response.json()["pdf_url"]
            st.sidebar.success("Reporte generado")
            st.sidebar.markdown(f"[Abrir reporte]({BACKEND_URL}{pdf_url})")
        else:
            st.sidebar.error(response.json().get("detail", "Error al generar reporte"))
    except Exception as e:
        st.sidebar.error(f"Error de conexión: {e}")

if st.sidebar.button("Generar Reporte Gerencial"):
    try:
        response = requests.post(f"{BACKEND_URL}/api/reports/management", timeout=30)
        if response.status_code == 200:
            pdf_url = response.json()["pdf_url"]
            st.sidebar.success("Reporte generado")
            st.sidebar.markdown(f"[Abrir reporte]({BACKEND_URL}{pdf_url})")
        else:
            st.sidebar.error("Error al generar reporte")
    except Exception as e:
        st.sidebar.error(f"Error de conexión: {e}")

# Métricas Principales
st.subheader("📈 Métricas del Día")
col1, col2, col3, col4 = st.columns(4)

try:
    sales_res = requests.get(f"{BACKEND_URL}/api/stats/daily-sales", timeout=20)
    if sales_res.status_code == 200:
        sales_data = sales_res.json()
        col1.metric("Pedidos Hoy", f"{sales_data['total_ventas_hoy']}")
        col2.metric("Ingresos Hoy", f"${sales_data.get('ingresos_hoy', 0):,.2f}")
        col3.metric("Ingresos Totales", f"${sales_data['ingresos_totales']:,.2f}")
    
    user_res = requests.get(f"{BACKEND_URL}/api/stats/user-metrics", timeout=20)
    if user_res.status_code == 200:
        user_data = user_res.json()
        col4.metric("Promedio de Compra", f"${user_data['promedio_compra_usuario']:,.2f}")
except Exception as e:
    st.error(f"No se pudieron cargar las métricas: {e}")

# Gráficos
st.divider()
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Top Productos más Vendidos")
    try:
        top_res = requests.get(f"{BACKEND_URL}/api/stats/top-products", timeout=20)
        if top_res.status_code == 200:
            top_data = top_res.json()
            df_top = pd.DataFrame(top_data)
            fig = px.bar(df_top, x="producto", y="ventas", color="producto", title="Unidades vendidas por producto")
            st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Error al cargar top productos: {e}")

with col_right:
    st.subheader("Distribución de Categorías")
    try:
        cat_res = requests.get(f"{BACKEND_URL}/api/stats/category-sales", timeout=20)
        if cat_res.status_code == 200:
            cat_data = cat_res.json()
            df_cat = pd.DataFrame(cat_data)
            if not df_cat.empty:
                fig_pie = px.pie(df_cat, values="ingresos", names="categoria", title="Ingresos por Categoría")
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("Aún no hay ventas por categoría.")
        else:
            st.error("No se pudo cargar la distribución de categorías.")
    except Exception as e:
        st.error(f"Error al cargar categorías: {e}")

st.divider()
st.info("Este dashboard consume datos en tiempo real desde la API de FastAPI.")
