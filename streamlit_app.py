import streamlit as st
import pandas as pd
import json

# Importar módulos refactorizados
from utils import init_session_state, get_logger, display_logs
from io_parser import safe_read_table
from solver import run_optimization
from visualization import render_map, render_metrics_and_tables

# Configuración de la página
st.set_page_config(
    page_title="Rout-2 | Optimización de Rutas (Corregido)",
    page_icon="✅",
    layout="wide"
)

# Inicializar estado de la sesión y logger
init_session_state()
logger = get_logger()

# --- BARRA LATERAL (UI de Configuración) ---
with st.sidebar:
    st.title("🚚 Rout-2: Panel de Control")
    st.info("App corregida y robustecida para Streamlit.")

    # 1. Carga de Archivo
    with st.expander("1. Cargar Archivo de Paradas", expanded=True):
        uploaded_file = st.file_uploader(
            "Sube un archivo (.csv, .xlsx, .ods)",
            type=['csv', 'xlsx', 'ods'],
            help="Columnas requeridas: id, lat, lon, demanda, is_depot (True/False)."
        )
        if uploaded_file:
            try:
                logger.info(f"Procesando archivo subido: {uploaded_file.name}")
                paradas_df = safe_read_table(uploaded_file)
                st.session_state.paradas_df = paradas_df
                st.session_state.resultados = None # Limpiar resultados anteriores
                st.success(f"Archivo '{uploaded_file.name}' cargado con {len(paradas_df)} paradas.")
                logger.info("Archivo procesado y validado correctamente.")
            except Exception as e:
                st.error(f"Error al procesar el archivo: {e}")
                logger.error(f"Fallo en safe_read_table: {e}", exc_info=False)
                st.session_state.paradas_df = None

    # 2. Configuración de Flota
    with st.expander("2. Configurar Flota", expanded=True):
        num_vehiculos = st.slider("Número de Vehículos", 1, 20, 3, key="num_vehiculos")
        capacidad_general = st.number_input("Capacidad por Vehículo", min_value=1, value=50, key="cap_vehiculos")
        
        vehiculos_list = [{'id': f'vehiculo_{i+1}', 'capacidad': capacidad_general} for i in range(num_vehiculos)]
        st.session_state.vehiculos_df = pd.DataFrame(vehiculos_list)
        st.write(f"Flota: {num_vehiculos} vehículos con capacidad {capacidad_general} c/u.")

    # 3. Parámetros de Simulación y Solver
    with st.expander("3. Parámetros Avanzados", expanded=False):
        st.number_input("Costo por KM", value=0.5, format="%.2f", key="costo_km")
        st.number_input("Velocidad Promedio (km/h)", value=40.0, format="%.1f", key="velocidad_kmh")
        st.number_input("Semilla Aleatoria (seed)", value=42, key="random_seed")
        st.selectbox(
            "Modo del Solver",
            options=["Híbrido (Recomendado)", "Solo Heurística Rápida"],
            key="solver_mode",
            help="Híbrido intenta el solver avanzado y usa la heurística como fallback."
        )

    # 4. Botón de Ejecución
    st.markdown("---")
    if st.button("🚀 Ejecutar Optimización", type="primary", use_container_width=True):
        if st.session_state.paradas_df is not None and not st.session_state.paradas_df.empty:
            with st.spinner("Optimizando rutas... Esto puede tardar unos segundos."):
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
                    st.error(f"Ocurrió un error crítico durante la optimización: {e}")
                    logger.error(f"Fallo en run_optimization: {e}", exc_info=False)
                    st.session_state.resultados = None
        else:
            st.warning("Por favor, carga los datos de las paradas antes de optimizar.")

# --- PANTALLA PRINCIPAL ---
st.header("Visualización de Rutas y Resultados")

if st.session_state.resultados:
    render_metrics_and_tables(st.session_state.resultados, st.session_state.paradas_df)
else:
    st.subheader("🗺️ Mapa de Paradas")
    if st.session_state.paradas_df is not None:
        render_map(st.session_state.paradas_df, None)
    else:
        st.info("Bienvenido. Comienza cargando un archivo de paradas desde el panel de la izquierda.")

# Panel de Logs al final de la página
display_logs()
