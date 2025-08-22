import streamlit as st
import pandas as pd
import json
from utils import init_session_state, get_logger, display_logs
from io_parser import safe_read_table
from solver import run_optimization
from visualization import render_map, render_metrics_and_tables

# --- Configuración de la Página y Estilos ---
st.set_page_config(
    page_title="Rout-2 | Optimizador de Rutas",
    page_icon="🚚",
    layout="wide"
)

# Inyectar CSS para un look más moderno
st.markdown("""
<style>
    /* Botón principal */
    .stButton > button {
        border-radius: 20px;
        border: 1px solid #4B8BBE;
        background-color: #4B8BBE;
        color: white;
        transition: all 0.2s ease-in-out;
    }
    .stButton > button:hover {
        border-color: #3D6F9A;
        background-color: #3D6F9A;
    }
    /* Estilo de los contenedores de métricas */
    div[data-testid="metric-container"] {
        background-color: #F0F2F6;
        border: 1px solid #F0F2F6;
        padding: 10px;
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

init_session_state()
logger = get_logger()

# --- Barra Lateral ---
with st.sidebar:
    st.title("🚚 Rout-2: Panel de Control")
    st.info("Configura y ejecuta la optimización de rutas.")

    with st.expander("📂 1. Cargar Archivo de Paradas", expanded=True):
        uploaded_file = st.file_uploader(
            "Sube un archivo (.csv, .xlsx, .ods)",
            type=['csv', 'xlsx', 'ods'],
            help="Columnas requeridas: id/nombre, lat, lon, demanda/pasajeros."
        )
        if uploaded_file:
            try:
                paradas_df = safe_read_table(uploaded_file)
                st.session_state.paradas_df = paradas_df
                st.session_state.resultados = None
                st.success(f"Archivo '{uploaded_file.name}' cargado.")
            except Exception as e:
                st.error(f"Error al procesar: {e}")
                st.session_state.paradas_df = None

    with st.expander("🚛 2. Configurar Flota", expanded=True):
        num_vehiculos = st.slider("Número de Vehículos", 1, 20, 3, key="num_vehiculos")
        capacidad_general = st.number_input("Capacidad por Vehículo", min_value=1, value=50, key="cap_vehiculos")
        
        vehiculos_list = [{'id': f'Vehículo {i+1}', 'capacidad': capacidad_general} for i in range(num_vehiculos)]
        st.session_state.vehiculos_df = pd.DataFrame(vehiculos_list)

    with st.expander("⚙️ 3. Parámetros Avanzados", expanded=False):
        st.number_input("Costo por KM", value=0.5, format="%.2f", key="costo_km")
        st.number_input("Velocidad Promedio (km/h)", value=40.0, format="%.1f", key="velocidad_kmh")
        st.number_input("Semilla Aleatoria (seed)", value=42, key="random_seed")
        st.selectbox(
            "Modo del Solver",
            options=["Híbrido (Recomendado)", "Solo Heurística Rápida"],
            key="solver_mode"
        )

    st.markdown("---")
    if st.button("🚀 Optimizar Rutas", use_container_width=True):
        if st.session_state.paradas_df is not None and not st.session_state.paradas_df.empty:
            with st.spinner("Calculando las mejores rutas..."):
                try:
                    force_fallback = (st.session_state.solver_mode == "Solo Heurística Rápida")
                    resultados = run_optimization(
                        paradas_df=st.session_state.paradas_df,
                        vehiculos_df=st.session_state.vehiculos_df,
                        costo_km=st.session_state.costo_km,
                        velocidad_kmh=st.session_state.velocidad_kmh,
                        random_seed=st.session_state.random_seed,
                        force_fallback=force_fallback
                    )
                    st.session_state.resultados = resultados
                    st.success("¡Optimización completada!")
                except Exception as e:
                    st.error(f"Error en la optimización: {e}")
                    st.session_state.resultados = None
        else:
            st.warning("Por favor, carga un archivo de paradas primero.")

# --- Pantalla Principal ---
st.header("Visualización de Rutas y Resultados")

if st.session_state.resultados:
    render_metrics_and_tables(st.session_state.resultados, st.session_state.paradas_df)
else:
    st.subheader("🗺️ Mapa de Paradas")
    if st.session_state.paradas_df is not None:
        render_map(st.session_state.paradas_df, None)
    else:
        st.info("Bienvenido. Comienza cargando un archivo desde el panel de la izquierda.")

display_logs()
