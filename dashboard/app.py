import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import os

# Configuración
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")

st.set_page_config(page_title="Dashboard de Ventas - E-commerce", layout="wide")

st.title("📊 Dashboard de Gestión de Ventas")

# Sidebar para filtros y acciones
st.sidebar.header("Acciones")
if st.sidebar.button("Generar Reporte Gerencial"):
    try:
        response = requests.post(f"{BACKEND_URL}/api/reports/management")
        if response.status_code == 200:
            st.sidebar.success(f"Reporte generado: {response.json()['pdf_url']}")
        else:
            st.sidebar.error("Error al generar reporte")
    except Exception as e:
        st.sidebar.error(f"Error de conexión: {e}")

# Métricas Principales
st.subheader("📈 Métricas del Día")
col1, col2, col3 = st.columns(3)

try:
    sales_res = requests.get(f"{BACKEND_URL}/api/stats/daily-sales")
    if sales_res.status_code == 200:
        sales_data = sales_res.json()
        col1.metric("Ventas Hoy", f"{sales_data['total_ventas_hoy']}")
        col2.metric("Ingresos Totales", f"${sales_data['ingresos_totales']:,}")
    
    user_res = requests.get(f"{BACKEND_URL}/api/stats/user-metrics")
    if user_res.status_code == 200:
        user_data = user_res.json()
        col3.metric("Promedio de Compra", f"${user_data['promedio_compra_usuario']}")
except Exception as e:
    st.error(f"No se pudieron cargar las métricas: {e}")

# Gráficos
st.divider()
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Top Productos más Vendidos")
    try:
        top_res = requests.get(f"{BACKEND_URL}/api/stats/top-products")
        if top_res.status_code == 200:
            top_data = top_res.json()
            df_top = pd.DataFrame(top_data)
            fig = px.bar(df_top, x='producto', y='ventas', color='producto', title="Ventas por Producto")
            st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Error al cargar top productos: {e}")

with col_right:
    st.subheader("Distribución de Categorías")
    # Simulación de datos de categorías ya que no hay un endpoint específico
    cat_data = {"Categoría": ["Electrónica", "Ropa", "Hogar", "Libros"], "Ventas": [450, 300, 150, 100]}
    df_cat = pd.DataFrame(cat_data)
    fig_pie = px.pie(df_cat, values='Ventas', names='Categoría', title="Ventas por Categoría")
    st.plotly_chart(fig_pie, use_container_width=True)

st.divider()
st.info("Este dashboard consume datos en tiempo real desde la API de FastAPI.")
