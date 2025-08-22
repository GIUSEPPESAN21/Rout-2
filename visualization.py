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
    tab1, tab2, tab3, tab4 = st_tabs(["🗺️ Mapa", "📊 Resumen", "📋 Detalle", "📥 Descargar"])

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
