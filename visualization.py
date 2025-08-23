import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from io import BytesIO
import streamlit.components.v1 as components
import json

def to_excel(df_dict):
    """
    Exporta un diccionario de DataFrames a un archivo Excel en memoria.
    Se han eliminado los estilos complejos para maximizar la compatibilidad.
    """
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sheet_name, df in df_dict.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    output.seek(0)
    return output

def generate_html_report(resumen_df, paradas_df):
    """Genera un informe HTML a partir de los resultados para la exportación a PDF."""
    paradas_dict = {p['id']: p for _, p in paradas_df.iterrows()}
    
    html = """
    <html>
    <head>
        <style>
            body { font-family: sans-serif; margin: 20px; }
            h1, h2, h3 { color: #1E3A8A; }
            table { border-collapse: collapse; width: 100%; margin-bottom: 2rem; font-size: 12px; }
            th, td { border: 1px solid #ddd; padding: 6px; text-align: left; }
            th { background-color: #f2f2f2; }
        </style>
    </head>
    <body>
        <h1>Informe de Rutas - Rout Now</h1>
    """
    
    df_reporte = resumen_df.copy()
    df_reporte.rename(columns={
        'vehiculo_id': 'Vehículo',
        'total_demanda': 'Demanda Total',
        'capacidad_utilizada_pct': '% Capacidad',
        'distancia_km': 'Distancia (km)',
        'costo_estimado': 'Costo ($)'
    }, inplace=True)

    html += "<h2>Resumen General de la Operación</h2>"
    html += df_reporte[['Vehículo', 'Demanda Total', '% Capacidad', 'Distancia (km)', 'Costo ($)']].to_html(index=False, justify='center')
    
    html += "<h2>Detalle por Ruta</h2>"
    for _, ruta in resumen_df.iterrows():
        html += f"<h3>{ruta['vehiculo_id']}</h3>"
        ruta_df = pd.DataFrame([paradas_dict[pid] for pid in ruta['secuencia_paradas_ids']])
        html += ruta_df[['id', 'lat', 'lon', 'demanda']].to_html(index=False, justify='center')
        
    html += "</body></html>"
    return html

def render_map(paradas_df, resultados):
    """Renderiza un mapa más atractivo con íconos y tooltips."""
    map_center = [paradas_df['lat'].mean(), paradas_df['lon'].mean()]
    m = folium.Map(location=map_center, zoom_start=12, tiles="cartodbpositron")

    depot_icon = folium.Icon(color='red', icon='warehouse', prefix='fa')
    stop_icon = folium.Icon(color='blue', icon='circle-dot', prefix='fa')

    for _, parada in paradas_df.iterrows():
        tooltip_text = f"<b>{parada['id']}</b><br>Demanda: {parada['demanda']}"
        icon_to_use = depot_icon if parada['is_depot'] else stop_icon
        folium.Marker([parada['lat'], parada['lon']], tooltip=tooltip_text, icon=icon_to_use).add_to(m)

    if resultados:
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
        depot = paradas_df[paradas_df['is_depot']].iloc[0]
        paradas_dict = {p['id']: p for _, p in paradas_df.iterrows()}
        
        for i, ruta in enumerate(resultados):
            points = [[depot['lat'], depot['lon']]] + [[paradas_dict[pid]['lat'], paradas_dict[pid]['lon']] for pid in ruta['secuencia_paradas_ids']] + [[depot['lat'], depot['lon']]]
            folium.PolyLine(points, color=colors[i % len(colors)], weight=4, opacity=0.8, tooltip=f"{ruta['vehiculo_id']} ({ruta['distancia_km']:.1f} km)").add_to(m)

    st_folium(m, width='100%', height=600, returned_objects=[])

def render_results_section(resultados, paradas_df):
    """Muestra la sección de resultados con opciones de descarga."""
    resumen_df = pd.DataFrame(resultados)
    
    st.subheader("Métricas Clave")
    col1, col2, col3 = st.columns(3)
    col1.metric("Vehículos Utilizados", f"{len(resumen_df)}")
    col2.metric("Distancia Total", f"{resumen_df['distancia_km'].sum():.2f} km")
    col3.metric("Costo Total", f"${resumen_df['costo_estimado'].sum():,.2f}")
    
    st.markdown("---")
    st.subheader("Resumen por Vehículo")
    
    df_display = resumen_df[['vehiculo_id', 'total_demanda', 'capacidad_utilizada_pct', 'distancia_km', 'costo_estimado']].copy()
    df_display.rename(columns={'vehiculo_id': 'Vehículo', 'total_demanda': 'Demanda Total', 'capacidad_utilizada_pct': '% Capacidad', 'distancia_km': 'Distancia (km)', 'costo_estimado': 'Costo ($)'}, inplace=True)
    
    st.dataframe(df_display, hide_index=True, use_container_width=True,
        column_config={"% Capacidad": st.column_config.ProgressColumn("Capacidad Utilizada", format="%.1f%%", min_value=0, max_value=100)})

    st.markdown("---")
    st.subheader("Descargar Informes")
    
    paradas_dict = {p['id']: p for _, p in paradas_df.iterrows()}
    informe_sheets = {"Resumen": df_display}
    for _, ruta in resumen_df.iterrows():
        sheet_name = f"Ruta {ruta['vehiculo_id']}"
        if len(sheet_name) > 31: sheet_name = sheet_name[:31]
        ruta_df = pd.DataFrame([paradas_dict[pid] for pid in ruta['secuencia_paradas_ids']])
        informe_sheets[sheet_name] = ruta_df[['id', 'lat', 'lon', 'demanda']]

    col_excel, col_pdf = st.columns(2)
    
    with col_excel:
        excel_data = to_excel(informe_sheets)
        st.download_button(label="📥 Descargar Informe (Excel)", data=excel_data, file_name="informe_de_rutas.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
            
    with col_pdf:
        html_report = generate_html_report(resumen_df, paradas_df)
        # Escapar el HTML para pasarlo de forma segura a JavaScript
        html_escaped = json.dumps(html_report)
        
        components.html(f"""
            <script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
            <button id="descargar_pdf" onclick="descargarPDF()">📄 Descargar Informe (PDF)</button>
            
            <script>
                // El contenido HTML del informe ahora está en una variable de JavaScript
                const informeHtml = {html_escaped};

                function descargarPDF() {{
                    const opt = {{
                        margin:       0.5,
                        filename:     'informe_de_rutas.pdf',
                        image:        {{ type: 'jpeg', quality: 0.98 }},
                        html2canvas:  {{ scale: 2 }},
                        jsPDF:        {{ unit: 'in', format: 'letter', orientation: 'portrait' }}
                    }};
                    // Generar el PDF directamente desde la variable, no desde un div oculto
                    html2pdf().from(informeHtml).set(opt).save();
                }}
            </script>
            <style>
                #descargar_pdf {{
                    width: 100%;
                    padding: 0.25rem 0.75rem;
                    border-radius: 0.5rem;
                    border: 1px solid rgba(49, 51, 63, 0.2);
                    background-color: #FFFFFF;
                    color: #31333F;
                    cursor: pointer;
                    line-height: 2.5;
                }}
                #descargar_pdf:hover {{
                    border-color: #FF4B4B;
                    color: #FF4B4B;
                }}
            </style>
        """, height=50)
