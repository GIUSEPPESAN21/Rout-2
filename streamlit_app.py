import streamlit as st
import pandas as pd
from utils import init_session_state, get_logger
from io_parser import safe_read_table
from solver import run_optimization
from visualization import render_map, render_results_section

# --- Configuración de la Página y Estilos ---
st.set_page_config(
    page_title="Rout Now | Metaheuristic Solution",
    page_icon="🚚",
    layout="wide"
)

# Inyectar CSS para un look más pulido
st.markdown("""
<style>
    /* Ocultar el menú de Streamlit y el footer para un look de app real */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    /* Estilo del header */
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
        color: #1E3A8A; /* Azul oscuro */
        margin: 0;
        font-weight: 600;
    }
    .header p {
        font-size: 1.1rem;
        color: #555;
        margin: 0;
        margin-left: 1rem;
    }
    .header .icon {
        font-size: 2.5rem;
        margin-right: 1rem;
    }
    /* Estilo de las pestañas */
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #F0F2F6;
        border-radius: 8px 8px 0 0;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #FFFFFF;
    }
</style>
""", unsafe_allow_html=True)

# Inicializar estado y logger
init_session_state()
logger = get_logger()

# --- Header ---
st.markdown(
    """
    <div class="header">
        <span class="icon">🚚</span>
        <div>
            <h1>Rout Now</h1>
            <p>Metaheuristic Solution</p>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# --- Layout Principal de Dos Columnas ---
col1, col2 = st.columns([1, 2]) # Columna de control 33%, columna de mapa 67%

# --- Columna 1: Panel de Control con Pestañas ---
with col1:
    st.subheader("Panel de Control")
    
    tab_config, tab_results, tab_about = st.tabs(["⚙️ Configuración", "📊 Resultados", "👤 Acerca de"])

    # Pestaña de Configuración
    with tab_config:
        with st.container(border=True):
            st.markdown("##### 1. Cargar Datos de Paradas")
            uploaded_file = st.file_uploader(
                "Sube un archivo (.csv, .xlsx, .ods)",
                type=['csv', 'xlsx', 'ods'],
                label_visibility="collapsed"
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

        with st.container(border=True):
            st.markdown("##### 2. Definir Flota")
            num_vehiculos = st.slider("Número de Vehículos", 1, 20, 3, key="num_vehiculos")
            capacidad_general = st.number_input("Capacidad por Vehículo", min_value=1, value=50, key="cap_vehiculos")
            
            vehiculos_list = [{'id': f'Vehículo {i+1}', 'capacidad': capacidad_general} for i in range(num_vehiculos)]
            st.session_state.vehiculos_df = pd.DataFrame(vehiculos_list)

        with st.container(border=True):
            st.markdown("##### 3. Parámetros de Simulación")
            col_costo, col_vel = st.columns(2)
            with col_costo:
                st.number_input("Costo por KM", value=0.5, format="%.2f", key="costo_km")
            with col_vel:
                st.number_input("Velocidad (km/h)", value=40.0, format="%.1f", key="velocidad_kmh")
        
        st.markdown("---")
        if st.button("🚀 Optimizar Rutas", use_container_width=True, type="primary"):
            if st.session_state.paradas_df is not None and not st.session_state.paradas_df.empty:
                with st.spinner("Calculando las mejores rutas..."):
                    try:
                        # La semilla aleatoria ahora es fija para consistencia, pero oculta al usuario
                        resultados = run_optimization(
                            paradas_df=st.session_state.paradas_df,
                            vehiculos_df=st.session_state.vehiculos_df,
                            costo_km=st.session_state.costo_km,
                            velocidad_kmh=st.session_state.velocidad_kmh,
                            random_seed=42, # Semilla fija
                            force_fallback=False
                        )
                        st.session_state.resultados = resultados
                        st.success("¡Optimización completada!")
                        st.toast("Resultados listos en la pestaña 'Resultados'.", icon="🎉")
                    except Exception as e:
                        st.error(f"Error en la optimización: {e}")
                        st.session_state.resultados = None
            else:
                st.warning("Por favor, carga un archivo de paradas primero.")

    # Pestaña de Resultados
    with tab_results:
        if st.session_state.resultados:
            render_results_section(st.session_state.resultados, st.session_state.paradas_df)
        else:
            st.info("Aún no se han generado resultados. Ejecuta la optimización en la pestaña 'Configuración'.")

    # Pestaña "Acerca de"
    with tab_about:
        st.markdown("##### Autor")
        st.write("**Joseph Javier Sánchez Acuña**")
        st.write("_Ingeniero Industrial, Experto en Inteligencia Artificial y Desarrollo de Software._")
        st.markdown("---")
        st.markdown("##### Contacto")
        st.write("🔗 [Perfil de LinkedIn](https://www.linkedin.com/in/joseph-javier-sánchez-acuña-150410275)")
        st.write("📂 [Repositorio en GitHub](https://github.com/GIUSEPPESAN21)")
        st.write("📧 joseph.sanchez@uniminuto.edu.co")


# --- Columna 2: Mapa (Siempre Visible) ---
with col2:
    st.subheader("Mapa de Operaciones")
    if st.session_state.paradas_df is not None:
        render_map(st.session_state.paradas_df, st.session_state.resultados)
    else:
        # Mapa de bienvenida si no hay datos
        st.image("https://i.imgur.com/3o5s48j.png", caption="Carga un archivo para visualizar las paradas en el mapa.")
