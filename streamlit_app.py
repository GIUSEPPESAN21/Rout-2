# streamlit_app.py
import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
from python_tsp.heuristics import solve_tsp_simulated_annealing
import math
import io
import json

# ==============================================================================
# --- CONFIGURACIÓN DE LA PÁGINA ---
# ==============================================================================
st.set_page_config(
    page_title="Rout-2 | Optimización de Rutas",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# --- LÓGICA DE OPTIMIZACIÓN (Refactorizada del backend original) ---
# ==============================================================================

# Usamos el cache de Streamlit para evitar recalcular distancias innecesariamente
@st.cache_data
def haversine(lat1, lon1, lat2, lon2):
    """Calcula la distancia haversine entre dos puntos en la tierra."""
    R = 6371000  # Radio de la Tierra en metros
    lat1_rad, lon1_rad, lat2_rad, lon2_rad = map(math.radians, [lat1, lon1, lat2, lon2])
    dlon, dlat = lon2_rad - lon1_rad, lat2_rad - lat1_rad
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    return R * 2 * math.asin(math.sqrt(a))

def solve_tsp_for_route(parada_ids, depot, paradas_dict):
    """Resuelve el Problema del Viajante (TSP) para una ruta específica."""
    nodos_ids = [depot['id']] + parada_ids
    dist_matrix = np.array([
        [haversine(paradas_dict[i]['lat'], paradas_dict[i]['lon'], paradas_dict[j]['lat'], paradas_dict[j]['lon']) for j in nodos_ids]
        for i in nodos_ids
    ])

    permutation, dist_m = solve_tsp_simulated_annealing(dist_matrix)

    nodos_ordenados = [nodos_ids[i] for i in permutation]
    start_idx = nodos_ordenados.index(depot['id'])
    secuencia_final_ids = nodos_ordenados[start_idx:] + nodos_ordenados[:start_idx]

    return {
        "secuencia_paradas_ids": [pid for pid in secuencia_final_ids if pid != depot['id']],
        "distancia_optima_m": dist_m,
    }

def assign_stops_to_vehicles(paradas_df, vehiculos_df, depot):
    """Asigna paradas a vehículos usando una heurística de vecino más cercano."""
    paradas_pendientes = paradas_df.copy().sort_values('demanda', ascending=False)
    asignaciones = {v_id: [] for v_id in vehiculos_df['id']}
    capacidad_restante = {row['id']: row['capacidad'] for _, row in vehiculos_df.iterrows()}
    
    for _, vehiculo in vehiculos_df.iterrows():
        vehiculo_id = vehiculo['id']
        last_pos = (depot['lat'], depot['lon'])
        
        while True:
            paradas_que_caben = paradas_pendientes[paradas_pendientes['demanda'] <= capacidad_restante[vehiculo_id]].copy()
            if paradas_que_caben.empty:
                break

            paradas_que_caben['dist_a_last'] = paradas_que_caben.apply(
                lambda row: haversine(last_pos[0], last_pos[1], row['lat'], row['lon']), axis=1
            )
            
            mejor_parada = paradas_que_caben.sort_values('dist_a_last').iloc[0]
            
            asignaciones[vehiculo_id].append(mejor_parada['id'])
            capacidad_restante[vehiculo_id] -= mejor_parada['demanda']
            paradas_pendientes = paradas_pendientes.drop(mejor_parada.name)
            last_pos = (mejor_parada['lat'], mejor_parada['lon'])
    
    if not paradas_pendientes.empty:
        st.warning(f"{len(paradas_pendientes)} paradas no pudieron ser asignadas. Intente con más vehículos o de mayor capacidad.")

    return asignaciones

@st.cache_data
def run_optimization(paradas_df, vehiculos_df, costo_km, velocidad_kmh):
    """Ejecuta el proceso completo de optimización de rutas."""
    if 'id' not in paradas_df.columns:
        paradas_df['id'] = [f'p_{i}' for i in range(len(paradas_df))]

    depot_row = paradas_df[paradas_df['is_depot']].iloc[0]
    depot = depot_row.to_dict()
    paradas_clientes_df = paradas_df[~paradas_df['is_depot']]

    if paradas_clientes_df.empty:
        st.error("No hay paradas de clientes para optimizar.")
        return None

    if paradas_clientes_df['demanda'].sum() > vehiculos_df['capacidad'].sum():
        st.error("La capacidad total de los vehículos es insuficiente para la demanda total de las paradas.")
        return None

    asignaciones = assign_stops_to_vehicles(paradas_clientes_df, vehiculos_df, depot)
    
    resultados = []
    paradas_dict = {p['id']: p for _, p in paradas_df.iterrows()}

    for vehiculo_id, parada_ids in asignaciones.items():
        if not parada_ids:
            continue
        
        ruta_optima_tsp = solve_tsp_for_route(parada_ids, depot, paradas_dict)
        
        vehiculo_info = vehiculos_df[vehiculos_df['id'] == vehiculo_id].iloc[0]
        total_demanda = paradas_clientes_df[paradas_clientes_df['id'].isin(parada_ids)]['demanda'].sum()
        capacidad_vehiculo = vehiculo_info['capacidad']
        utilizacion_pct = (total_demanda / capacidad_vehiculo) * 100 if capacidad_vehiculo > 0 else 0
        distancia_km = ruta_optima_tsp['distancia_optima_m'] / 1000
        tiempo_h = distancia_km / velocidad_kmh if velocidad_kmh > 0 else 0
        
        resultados.append({
            "vehiculo_id": vehiculo_id,
            "capacidad": int(capacidad_vehiculo),
            "total_demanda": int(total_demanda),
            "capacidad_utilizada_pct": utilizacion_pct,
            "distancia_km": distancia_km,
            "costo_estimado": distancia_km * costo_km,
            "tiempo_estimado_h": tiempo_h,
            **ruta_optima_tsp
        })
    
    return sorted(resultados, key=lambda x: int(str(x['vehiculo_id']).split('_')[-1]))

# ==============================================================================
# --- FUNCIONES AUXILIARES DE LA UI ---
# ==============================================================================

def inicializar_estado():
    """Inicializa el estado de la sesión de Streamlit."""
    if 'paradas_df' not in st.session_state:
        st.session_state.paradas_df = None
    if 'vehiculos_df' not in st.session_state:
        st.session_state.vehiculos_df = pd.DataFrame(columns=['id', 'capacidad'])
    if 'resultados' not in st.session_state:
        st.session_state.resultados = None
    if 'map_center' not in st.session_state:
        st.session_state.map_center = [4.60971, -74.08175] # Bogotá como default

def parse_uploaded_file(uploaded_file):
    """Parsea un archivo CSV o Excel a un DataFrame de Pandas."""
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        elif uploaded_file.name.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(uploaded_file)
        else:
            st.error("Formato de archivo no soportado. Por favor, suba un archivo CSV o Excel.")
            return None
        
        # Normalizar nombres de columnas
        df.columns = [str(c).lower().strip().replace(' ', '_') for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Error al leer el archivo: {e}")
        return None

def render_map(paradas_df, resultados):
    """Renderiza el mapa con las paradas y las rutas."""
    if paradas_df is not None and not paradas_df.empty:
        map_center = [paradas_df['lat'].mean(), paradas_df['lon'].mean()]
    else:
        map_center = st.session_state.map_center

    m = folium.Map(location=map_center, zoom_start=12)

    colors = ['#ff00ff', '#00ff00', '#00ffff', '#ff8c00', '#ff1493', '#adff2f', '#48d1cc', '#ff4500']

    if paradas_df is not None:
        for _, parada in paradas_df.iterrows():
            popup_text = f"<b>ID:</b> {parada['id']}<br><b>Demanda:</b> {parada['demanda']}"
            if parada['is_depot']:
                folium.Marker(
                    [parada['lat'], parada['lon']],
                    popup=popup_text,
                    icon=folium.Icon(color='red', icon='home')
                ).add_to(m)
            else:
                folium.Marker(
                    [parada['lat'], parada['lon']],
                    popup=popup_text,
                    icon=folium.Icon(color='blue', icon='info-sign')
                ).add_to(m)

    if resultados:
        depot = paradas_df[paradas_df['is_depot']].iloc[0]
        paradas_dict = {p['id']: p for _, p in paradas_df.iterrows()}
        
        for i, ruta in enumerate(resultados):
            color = colors[i % len(colors)]
            points = [[depot['lat'], depot['lon']]]
            for parada_id in ruta['secuencia_paradas_ids']:
                parada = paradas_dict.get(parada_id)
                if parada is not None:
                    points.append([parada['lat'], parada['lon']])
            points.append([depot['lat'], depot['lon']])
            
            folium.PolyLine(points, color=color, weight=2.5, opacity=1, popup=f"Vehículo {ruta['vehiculo_id']}").add_to(m)

    st_folium(m, width='100%', height=600)

# ==============================================================================
# --- INTERFAZ DE USUARIO (UI) ---
# ==============================================================================

inicializar_estado()

# --- BARRA LATERAL ---
with st.sidebar:
    st.title("🚚 Rout-2: Panel de Control")
    st.markdown("Configura y ejecuta la optimización de rutas.")

    # --- Carga de Archivo ---
    with st.expander("1. Cargar Archivo de Paradas", expanded=True):
        uploaded_file = st.file_uploader(
            "Sube un archivo CSV o Excel",
            type=['csv', 'xlsx'],
            help="El archivo debe contener columnas como 'id', 'lat', 'lon', 'demanda' y una columna 'is_depot' (TRUE/FALSE) para identificar el depósito."
        )
        if uploaded_file:
            df = parse_uploaded_file(uploaded_file)
            if df is not None:
                # Validar columnas necesarias
                required_cols = {'id', 'lat', 'lon', 'demanda', 'is_depot'}
                if not required_cols.issubset(df.columns):
                    st.error(f"El archivo debe contener las columnas: {', '.join(required_cols)}")
                else:
                    st.session_state.paradas_df = df
                    st.success(f"Archivo '{uploaded_file.name}' cargado con {len(df)} paradas.")

        st.markdown("O usa datos de ejemplo:")
        if st.button("Cargar datos de prueba"):
            sample_data = {
                'id': [f'depot_0', 'stop_1', 'stop_2', 'stop_3', 'stop_4', 'stop_5'],
                'lat': [4.62, 4.65, 4.68, 4.61, 4.58, 4.66],
                'lon': [-74.07, -74.05, -74.08, -74.10, -74.06, -74.11],
                'demanda': [0, 10, 15, 8, 12, 20],
                'is_depot': [True, False, False, False, False, False]
            }
            st.session_state.paradas_df = pd.DataFrame(sample_data)
            st.success("Datos de prueba cargados.")

    # --- Configuración de Vehículos ---
    with st.expander("2. Configurar Flota", expanded=True):
        num_vehiculos = st.slider("Número de Vehículos", 1, 20, 3)
        capacidad_general = st.number_input("Capacidad por Vehículo (uniforme)", min_value=1, value=50)
        
        vehiculos_list = []
        for i in range(num_vehiculos):
            vehiculos_list.append({'id': f'vehiculo_{i+1}', 'capacidad': capacidad_general})
        st.session_state.vehiculos_df = pd.DataFrame(vehiculos_list)
        st.write(f"Flota: {num_vehiculos} vehículos con capacidad de {capacidad_general} cada uno.")

    # --- Parámetros de Optimización ---
    with st.expander("3. Parámetros de Simulación", expanded=True):
        costo_km = st.number_input("Costo por KM (ej: en USD)", value=0.5, format="%.2f")
        velocidad_kmh = st.number_input("Velocidad Promedio (km/h)", value=40.0, format="%.1f")
        
    # --- Botón de Ejecución ---
    st.markdown("---")
    if st.button("🚀 Ejecutar Optimización", type="primary", use_container_width=True):
        if st.session_state.paradas_df is not None and not st.session_state.paradas_df.empty:
            with st.spinner("Optimizando rutas... por favor espera."):
                resultados = run_optimization(
                    st.session_state.paradas_df,
                    st.session_state.vehiculos_df,
                    costo_km,
                    velocidad_kmh
                )
                st.session_state.resultados = resultados
        else:
            st.warning("Por favor, carga los datos de las paradas antes de optimizar.")

# --- PANTALLA PRINCIPAL ---
st.header("Visualización de Rutas y Resultados")

if st.session_state.paradas_df is None:
    st.info("Bienvenido a Rout-2. Comienza cargando un archivo de paradas desde el panel de la izquierda.")

# --- Pestañas de Resultados ---
if st.session_state.resultados is not None:
    tab1, tab2, tab3, tab4 = st.tabs(["🗺️ Mapa de Rutas", "📊 Resumen de Resultados", "📋 Detalle por Ruta", "📥 Descargar Datos"])

    with tab1:
        st.subheader("Mapa Interactivo de Rutas")
        render_map(st.session_state.paradas_df, st.session_state.resultados)

    with tab2:
        st.subheader("Métricas Generales de la Optimización")
        resumen_df = pd.DataFrame(st.session_state.resultados)
        
        total_distancia = resumen_df['distancia_km'].sum()
        total_costo = resumen_df['costo_estimado'].sum()
        total_tiempo = resumen_df['tiempo_estimado_h'].sum()
        vehiculos_usados = len(resumen_df)
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Vehículos Utilizados", f"{vehiculos_usados}/{len(st.session_state.vehiculos_df)}")
        col2.metric("Distancia Total", f"{total_distancia:.2f} km")
        col3.metric("Costo Total Estimado", f"${total_costo:,.2f}")
        col4.metric("Tiempo Total de Viaje", f"{total_tiempo:.2f} h")
        
        st.dataframe(resumen_df[[
            "vehiculo_id", "total_demanda", "capacidad", "capacidad_utilizada_pct", 
            "distancia_km", "costo_estimado", "tiempo_estimado_h"
        ]].style.format({
            "capacidad_utilizada_pct": "{:.2f}%",
            "distancia_km": "{:.2f}",
            "costo_estimado": "${:,.2f}",
            "tiempo_estimado_h": "{:.2f}"
        }))

    with tab3:
        st.subheader("Detalle de Paradas por Ruta")
        paradas_dict = {p['id']: p for _, p in st.session_state.paradas_df.iterrows()}
        for ruta in st.session_state.resultados:
            with st.container(border=True):
                st.markdown(f"#### Ruta para **{ruta['vehiculo_id']}**")
                
                ruta_paradas_df = pd.DataFrame([paradas_dict[pid] for pid in ruta['secuencia_paradas_ids']])
                st.dataframe(ruta_paradas_df[['id', 'lat', 'lon', 'demanda']])

    with tab4:
        st.subheader("Exportar Resultados")
        
        # Preparar CSV para descarga
        resumen_csv = resumen_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Descargar Resumen de Rutas (CSV)",
            data=resumen_csv,
            file_name="resumen_rutas.csv",
            mime="text/csv",
        )
        
        # Preparar GeoJSON para descarga
        features = []
        depot = st.session_state.paradas_df[st.session_state.paradas_df['is_depot']].iloc[0]
        for ruta in st.session_state.resultados:
            coords = [[depot['lon'], depot['lat']]]
            for parada_id in ruta['secuencia_paradas_ids']:
                parada = paradas_dict.get(parada_id)
                if parada is not None:
                    coords.append([parada['lon'], parada['lat']])
            coords.append([depot['lon'], depot['lat']])
            
            features.append({
                "type": "Feature",
                "properties": {
                    "vehiculo_id": ruta['vehiculo_id'],
                    "distancia_km": ruta['distancia_km']
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": coords
                }
            })
        
        geojson_data = {
            "type": "FeatureCollection",
            "features": features
        }
        
        st.download_button(
            label="Descargar Rutas (GeoJSON)",
            data=json.dumps(geojson_data, indent=2),
            file_name="rutas_optimizadas.geojson",
            mime="application/json",
        )

else:
    # Mostrar mapa vacío si no hay resultados
    st.subheader("Mapa de Paradas")
    render_map(st.session_state.paradas_df, None)

# --- Panel de Logs (simulado) ---
with st.expander("Ver Logs y Datos Crudos"):
    st.write("Paradas Cargadas:")
    st.dataframe(st.session_state.paradas_df)
    st.write("Flota Configurada:")
    st.dataframe(st.session_state.vehiculos_df)
    st.write("Resultados de Optimización (JSON):")
    st.json(st.session_state.resultados if st.session_state.resultados else "Aún no hay resultados.")
