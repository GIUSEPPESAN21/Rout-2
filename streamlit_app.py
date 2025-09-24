import streamlit as st
import pandas as pd
from utils import init_session_state, get_logger
from io_parser import safe_read_table
from solver import run_optimization
from visualization import render_map, render_results_section # Se mantiene tu visualizador
import folium
from streamlit_folium import st_folium

# --- Configuración de la Página y Estilos ---
st.set_page_config(
    page_title="Rout Now | Fusión Mejorada",
    page_icon="🚚",
    layout="wide"
)

# Inyectar CSS (se mantiene tu estilo original)
st.markdown("""
<style>
    /* Estilos originales de Rout Now */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .header {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        display: flex;
        align-items: center;
    }
    .header h1 {
        font-size: 2.5rem;
        color: #1E3A8A;
        margin: 0;
        font-weight: 600;
    }
    /* ... (resto de tu CSS se mantiene) ... */
</style>
""", unsafe_allow_html=True)

# --- Inicializar Estado y Logger ---
init_session_state()
logger = get_logger()

# Novedad: Inicializar coordenadas del depósito en el session_state
if 'depot_lat' not in st.session_state:
    st.session_state.depot_lat = 4.4389   # Coordenadas por defecto (ej. Tuluá, Valle)
if 'depot_lon' not in st.session_state:
    st.session_state.depot_lon = -76.1951

# --- Header (se mantiene el tuyo) ---
st.markdown(
    """
    <div class="header">
        <span class="icon">🚚</span>
        <div>
            <h1>Rout Now</h1>
            <p>Metaheuristic Solution (Interfaz Mejorada)</p>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# --- Layout Principal (Ahora con pestañas como en ACO) ---
tab_config, tab_results, tab_about = st.tabs(["⚙️ Configuración", "📊 Resultados", "👤 Acerca de"])

# --- Pestaña de Configuración ---
with tab_config:
    col1, col2 = st.columns([0.6, 0.4]) # Dividir en dos columnas

    with col1:
        st.subheader("1. Cargar Datos de Paradas (Clientes)")
        uploaded_file = st.file_uploader(
            "Sube un archivo (.csv, .xlsx, .ods) SIN la fila del depósito.",
            type=['csv', 'xlsx', 'ods']
        )
        if uploaded_file:
            try:
                # El parser ahora no exigirá un depósito en el archivo
                paradas_df = safe_read_table(uploaded_file)
                st.session_state.paradas_df = paradas_df
                st.session_state.resultados = None # Limpiar resultados antiguos
                st.success(f"Archivo '{uploaded_file.name}' cargado con {len(paradas_df)} paradas.")
            except Exception as e:
                st.error(f"Error al procesar: {e}")
                st.session_state.paradas_df = None

        st.subheader("2. Definir Ubicación del Depósito")
        st.info("Haz clic en el mapa para establecer el punto de partida y regreso.")

        # Mapa para seleccionar el depósito (lógica de ACO)
        map_center = [st.session_state.depot_lat, st.session_state.depot_lon]
        if st.session_state.paradas_df is not None:
            map_center = [st.session_state.paradas_df['lat'].mean(), st.session_state.paradas_df['lon'].mean()]

        m_config = folium.Map(location=map_center, zoom_start=12, tiles="cartodbpositron")
        # Marcador del depósito actual
        folium.Marker(
            [st.session_state.depot_lat, st.session_state.depot_lon],
            popup="Depósito Actual", tooltip="Depósito",
            icon=folium.Icon(color="red", icon="warehouse", prefix='fa')
        ).add_to(m_config)

        # Marcadores de las paradas cargadas
        if st.session_state.paradas_df is not None:
            for _, row in st.session_state.paradas_df.iterrows():
                folium.Marker([row['lat'], row['lon']], tooltip=row['id']).add_to(m_config)

        map_data = st_folium(m_config, width=700, height=400, key="depot_map")
        if map_data and map_data["last_clicked"]:
            st.session_state.depot_lat = map_data["last_clicked"]["lat"]
            st.session_state.depot_lon = map_data["last_clicked"]["lng"]
            st.rerun() # Recargar para actualizar la coordenada mostrada

    with col2:
        st.subheader("3. Parámetros de la Flota")
        st.write(f"**Depósito Seleccionado:**")
        st.code(f"Lat: {st.session_state.depot_lat:.5f}, Lon: {st.session_state.depot_lon:.5f}")
        num_vehiculos = st.slider("Número de Vehículos", 1, 20, 3, key="num_vehiculos")
        capacidad_general = st.number_input("Capacidad por Vehículo", min_value=1, value=50, key="cap_vehiculos")
        st.session_state.vehiculos_df = pd.DataFrame(
            [{'id': f'Vehículo {i+1}', 'capacidad': capacidad_general} for i in range(num_vehiculos)]
        )

        st.subheader("4. Parámetros de Simulación")
        costo_km = st.number_input("Costo por KM ($)", value=1500.0, format="%.2f", key="costo_km")
        velocidad_kmh = st.number_input("Velocidad (km/h)", value=60.0, format="%.1f", key="velocidad_kmh")

    st.divider()
    if st.button("🚀 Optimizar Rutas", type="primary", use_container_width=True):
        if st.session_state.paradas_df is None or st.session_state.paradas_df.empty:
            st.warning("Por favor, carga primero un archivo de paradas.")
        else:
            with st.spinner("Calculando las mejores rutas..."):
                try:
                    # --- Lógica de Integración Clave ---
                    # 1. Crear el DataFrame del depósito a partir de la selección manual
                    depot_df = pd.DataFrame([{
                        'id': 'depot',
                        'lat': st.session_state.depot_lat,
                        'lon': st.session_state.depot_lon,
                        'demanda': 0,
                        'is_depot': True
                    }])
                    # 2. Combinar el depósito con las paradas del cliente
                    full_paradas_df = pd.concat([depot_df, st.session_state.paradas_df], ignore_index=True)

                    # 3. Ejecutar la optimización con el DataFrame completo
                    resultados = run_optimization(
                        paradas_df=full_paradas_df,
                        vehiculos_df=st.session_state.vehiculos_df,
                        costo_km=st.session_state.costo_km,
                        velocidad_kmh=st.session_state.velocidad_kmh,
                        random_seed=42,
                        force_fallback=False
                    )
                    st.session_state.resultados = resultados
                    # Guardamos el DF completo para usarlo en la visualización
                    st.session_state.full_paradas_df = full_paradas_df
                    st.success("¡Optimización completada!")
                    st.toast("Resultados listos en la pestaña 'Resultados'.", icon="🎉")
                except Exception as e:
                    st.error(f"Error en la optimización: {e}")
                    st.session_state.resultados = None

# --- Pestaña de Resultados ---
with tab_results:
    if st.session_state.resultados:
        st.header("Análisis de la Solución Optimizada")
        # Visualización del Mapa
        st.subheader("🗺️ Visualización de Rutas Optimizadas")
        render_map(st.session_state.full_paradas_df, st.session_state.resultados)
        
        # Nueva sección de resultados (inspirada en ACO)
        render_results_section(st.session_state.resultados, st.session_state.full_paradas_df)
    else:
        st.info("Completa y ejecuta la configuración para ver los resultados.")

# --- Pestaña "Acerca de" ---
with tab_about:
    st.markdown("##### Autor")
    st.write("**Joseph Javier Sánchez Acuña**")
    # ... (resto de tu información de contacto) ...
