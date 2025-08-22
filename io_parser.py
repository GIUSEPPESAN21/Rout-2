# --- io_parser.py ---
import pandas as pd
import streamlit as st
from io import BytesIO

REQUIRED_COLUMNS = ['id', 'lat', 'lon', 'demanda', 'is_depot']

def normalize_columns(df):
    """Normaliza los nombres de las columnas a un formato estándar."""
    cols = {col: col.lower().strip().replace(' ', '_') for col in df.columns}
    df = df.rename(columns=cols)
    return df

def validate_dataframe(df):
    """Valida que el DataFrame tenga las columnas y tipos de datos necesarios."""
    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Faltan columnas obligatorias: {', '.join(missing_cols)}")

    try:
        df['lat'] = pd.to_numeric(df['lat'])
        df['lon'] = pd.to_numeric(df['lon'])
        df['demanda'] = pd.to_numeric(df['demanda'])
        df['is_depot'] = df['is_depot'].astype(bool)
    except Exception as e:
        raise TypeError(f"Error en tipos de datos. lat/lon/demanda deben ser numéricos. Error: {e}")

    if df['is_depot'].sum() != 1:
        raise ValueError(f"Debe haber exactamente un depósito (una fila con 'is_depot' en True). Se encontraron {df['is_depot'].sum()}.")
        
    return df

@st.cache_data(show_spinner=False)
def safe_read_table(_uploaded_file):
    """Lee un archivo de forma segura, probando diferentes encodings y validando."""
    file_content = BytesIO(_uploaded_file.getvalue())
    file_name = _uploaded_file.name.lower()
    df = None
    
    encodings_to_try = ['utf-8', 'latin-1', 'cp1252']
    
    for encoding in encodings_to_try:
        try:
            file_content.seek(0)
            if file_name.endswith('.csv'):
                df = pd.read_csv(file_content, sep=None, engine='python', encoding=encoding)
            elif file_name.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file_content, engine='openpyxl')
            elif file_name.endswith('.ods'):
                df = pd.read_excel(file_content, engine='odf')
            
            if df is not None:
                break
        except (UnicodeDecodeError, Exception):
            continue
    
    if df is None:
        raise ValueError("No se pudo leer el archivo. Verifique el formato y la codificación (UTF-8, Latin-1).")

    df = normalize_columns(df)
    df = validate_dataframe(df)
    
    return df

# --- streamlit_app.py ---
import streamlit as st
import pandas as pd
import json
from utils import init_session_state, get_logger, display_logs
from io_parser import safe_read_table
from solver import run_optimization
from visualization import render_map, render_metrics_and_tables

st.set_page_config(
    page_title="Rout-2 | Optimización de Rutas (Corregido)",
    page_icon="✅",
    layout="wide"
)

init_session_state()
logger = get_logger()

with st.sidebar:
    st.title("🚚 Rout-2: Panel de Control")
    st.info("App corregida y robustecida para Streamlit.")

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
                st.session_state.resultados = None
                st.success(f"Archivo '{uploaded_file.name}' cargado con {len(paradas_df)} paradas.")
                logger.info("Archivo procesado y validado correctamente.")
            except Exception as e:
                st.error(f"Error al procesar el archivo: {e}")
                logger.error(f"Fallo en safe_read_table: {e}", exc_info=False)
                st.session_state.paradas_df = None

    with st.expander("2. Configurar Flota", expanded=True):
        num_vehiculos = st.slider("Número de Vehículos", 1, 20, 3, key="num_vehiculos")
        capacidad_general = st.number_input("Capacidad por Vehículo", min_value=1, value=50, key="cap_vehiculos")
        
        vehiculos_list = [{'id': f'vehiculo_{i+1}', 'capacidad': capacidad_general} for i in range(num_vehiculos)]
        st.session_state.vehiculos_df = pd.DataFrame(vehiculos_list)
        st.write(f"Flota: {num_vehiculos} vehículos con capacidad {capacidad_general} c/u.")

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

    st.markdown("---")
    if st.button("🚀 Ejecutar Optimización", type="primary", use_container_width=True):
        if st.session_state.paradas_df is not None and not st.session_state.paradas_df.empty:
            with st.spinner("Optimizando rutas..."):
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

st.header("Visualización de Rutas y Resultados")

if st.session_state.resultados:
    render_metrics_and_tables(st.session_state.resultados, st.session_state.paradas_df)
else:
    st.subheader("🗺️ Mapa de Paradas")
    if st.session_state.paradas_df is not None:
        render_map(st.session_state.paradas_df, None)
    else:
        st.info("Bienvenido. Comienza cargando un archivo de paradas desde el panel de la izquierda.")

display_logs()

# --- utils.py ---
import streamlit as st
import logging

def init_session_state():
    """Inicializa las variables necesarias en el st.session_state."""
    if 'paradas_df' not in st.session_state:
        st.session_state.paradas_df = None
    if 'vehiculos_df' not in st.session_state:
        st.session_state.vehiculos_df = None
    if 'resultados' not in st.session_state:
        st.session_state.resultados = None
    if 'logs' not in st.session_state:
        st.session_state.logs = []

def get_logger():
    """Configura y devuelve un logger que escribe en st.session_state."""
    logger = logging.getLogger("Rout2App")
    
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        class StreamlitLogHandler(logging.Handler):
            def emit(self, record):
                log_entry = self.format(record)
                st.session_state.logs.insert(0, log_entry)

        handler = StreamlitLogHandler()
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
    return logger

def display_logs():
    """Muestra los logs acumulados en un expander en la UI."""
    with st.expander("📋 Ver Logs de la Sesión"):
        if st.session_state.logs:
            log_text = "\n".join(st.session_state.logs)
            st.code(log_text, language="log")
        else:
            st.write("No hay logs para esta sesión todavía.")

# --- visualization.py ---
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import json

def render_map(paradas_df, resultados):
    """Renderiza el mapa interactivo con paradas y rutas."""
    map_center = [paradas_df['lat'].mean(), paradas_df['lon'].mean()]
    m = folium.Map(location=map_center, zoom_start=12)

    for _, parada in paradas_df.iterrows():
        popup = f"<b>ID:</b> {parada['id']}<br><b>Demanda:</b> {parada['demanda']}"
        icon = folium.Icon(color='red', icon='home') if parada['is_depot'] else folium.Icon(color='blue', icon='info-sign')
        folium.Marker([parada['lat'], parada['lon']], popup=popup, icon=icon).add_to(m)

    if resultados:
        colors = ['#ff00ff', '#00ff00', '#00ffff', '#ff8c00', '#ff1493', '#adff2f']
        depot = paradas_df[paradas_df['is_depot']].iloc[0]
        paradas_dict = {p['id']: p for _, p in paradas_df.iterrows()}
        
        for i, ruta in enumerate(resultados):
            points = [[depot['lat'], depot['lon']]] + [[paradas_dict[pid]['lat'], paradas_dict[pid]['lon']] for pid in ruta['secuencia_paradas_ids']] + [[depot['lat'], depot['lon']]]
            folium.PolyLine(points, color=colors[i % len(colors)], weight=3, opacity=0.8, popup=f"Ruta {ruta['vehiculo_id']}").add_to(m)

    st_folium(m, width='100%', height=500, returned_objects=[])

def render_metrics_and_tables(resultados, paradas_df):
    """Muestra las pestañas con el mapa, métricas, detalles y opciones de descarga."""
    tab1, tab2, tab3, tab4 = st.tabs(["🗺️ Mapa", "📊 Resumen", "📋 Detalle", "📥 Descargar"])

    with tab1:
        st.subheader("Mapa Interactivo de Rutas")
        render_map(paradas_df, resultados)

    with tab2:
        st.subheader("Métricas Generales")
        resumen_df = pd.DataFrame(resultados).drop(columns=['secuencia_paradas_ids'])
        st.metric("Vehículos Utilizados", f"{len(resumen_df)}")
        st.metric("Distancia Total", f"{resumen_df['distancia_km'].sum():.2f} km")
        st.dataframe(resumen_df)

    with tab3:
        st.subheader("Detalle de Paradas por Ruta")
        paradas_dict = {p['id']: p for _, p in paradas_df.iterrows()}
        for ruta in resultados:
            with st.container(border=True):
                st.markdown(f"#### Ruta para **{ruta['vehiculo_id']}**")
                ruta_df = pd.DataFrame([paradas_dict[pid] for pid in ruta['secuencia_paradas_ids']])
                st.dataframe(ruta_df[['id', 'lat', 'lon', 'demanda']])
    
    with tab4:
        st.subheader("Exportar Resultados")
        resumen_df = pd.DataFrame(resultados)
        csv = resumen_df.to_csv(index=False).encode('utf-8')
        st.download_button("Descargar Resumen (CSV)", csv, "resumen_rutas.csv", "text/csv")
