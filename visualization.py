import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from io import BytesIO
import json
import streamlit.components.v1 as components

def to_excel(df_dict):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sheet_name, df in df_dict.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    output.seek(0)
    return output

def generate_html_report(resumen_df, paradas_df):
    paradas_dict = {p['id']: p for _, p in paradas_df.iterrows()}
    html = """
    <html>
    <head><style>
        body { font-family: sans-serif; margin: 20px; }
        h1, h2, h3 { color: #1E3A8A; }
        table { border-collapse: collapse; width: 100%; margin-bottom: 2rem; font-size: 12px; }
        th, td { border: 1px solid #ddd; padding: 6px; text-align: left; }
        th { background-color: #f2f2f2; }
        .page-break { page-break-before: always; }
        .no-break { page-break-inside: avoid; }
    </style></head>
    <body><h1>Informe de Rutas - Rout Now</h1>
    """
    if not resumen_df.empty:
        df_reporte = resumen_df.copy()
        df_reporte.rename(columns={
            'vehiculo_id': 'Vehículo', 'total_demanda': 'Demanda Total',
            'capacidad_utilizada_pct': '% Capacidad', 'distancia_km': 'Distancia (km)',
            'costo_estimado': 'Costo ($)'
        }, inplace=True)
        html += "<div class='no-break'><h2>Resumen General</h2>"
        html += df_reporte[['Vehículo', 'Demanda Total', '% Capacidad', 'Distancia (km)', 'Costo ($)']].to_html(index=False, justify='center')
        html += "</div><h2 class='page-break'>Detalle por Ruta</h2>"
        for _, ruta in resumen_df.iterrows():
            html += f"<div class='no-break'><h3>{ruta['vehiculo_id']}</h3>"
            ruta_df = pd.DataFrame([paradas_dict[pid] for pid in ruta['secuencia_paradas_ids']])
            html += ruta_df[['id', 'lat', 'lon', 'demanda']].to_html(index=False, justify='center')
            html += "</div>"
    html += "</body></html>"
    return html

def render_map(paradas_df, resultados):
    if paradas_df is None or paradas_df.empty:
        st.warning("No hay datos de paradas para mostrar en el mapa.")
        return
    map_center = [paradas_df['lat'].mean(), paradas_df['lon'].mean()]
    m = folium.Map(location=map_center, zoom_start=12, tiles="cartodbpositron")
    depot_icon = folium.Icon(color='red', icon='warehouse', prefix='fa')
    stop_icon = folium.Icon(color='blue', icon='circle-dot', prefix='fa')
    for _, parada in paradas_df.iterrows():
        tooltip = f"<b>{parada.get('id', 'N/A')}</b><br>Demanda: {parada.get('demanda', 0)}"
        icon = depot_icon if parada.get('is_depot') else stop_icon
        folium.Marker([parada['lat'], parada['lon']], tooltip=tooltip, icon=icon).add_to(m)
    if resultados:
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
        depot = paradas_df[paradas_df['is_depot']].iloc[0]
        paradas_dict = {p['id']: p for _, p in paradas_df.iterrows()}
        for i, ruta in enumerate(resultados):
            points = [[depot['lat'], depot['lon']]] + \
                     [[paradas_dict[pid]['lat'], paradas_dict[pid]['lon']] for pid in ruta['secuencia_paradas_ids']] + \
                     [[depot['lat'], depot['lon']]]
            folium.PolyLine(points, color=colors[i % len(colors)], weight=4, opacity=0.8,
                            tooltip=f"{ruta['vehiculo_id']} ({ruta['distancia_km']:.1f} km)").add_to(m)
    st_folium(m, width='100%', height=500, returned_objects=[])

def render_results_section(resultados, paradas_df):
    if not resultados:
        st.warning("La optimización se completó, pero no se generaron rutas con los parámetros actuales. Intenta aumentar la capacidad o el número de vehículos.")
        return

    resumen_df = pd.DataFrame(resultados)
    st.subheader("📈 Resumen Ejecutivo")
    total_distancia = resumen_df['distancia_km'].sum()
    total_costo = resumen_df['costo_estimado'].sum()
    total_tiempo_h = resumen_df['tiempo_estimado_h'].sum()
    def format_duration(hours):
        h = int(hours); m = int((hours - h) * 60)
        return f"{h}h {m}min"

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Vehículos Utilizados", f"{len(resumen_df)}")
    m2.metric("Distancia Total", f"{total_distancia:.2f} km")
    m3.metric("Costo Total", f"${total_costo:,.2f}")
    m4.metric("Tiempo Total", f"{format_duration(total_tiempo_h)}")
    st.markdown("---")

    st.subheader("📋 Detalles por Ruta")
    paradas_dict = {p['id']: p for _, p in paradas_df.iterrows()}
    for i, ruta_info in enumerate(resumen_df.to_dict('records')):
        cap_pct = ruta_info.get('capacidad_utilizada_pct', 0)
        title = (f"**{ruta_info['vehiculo_id']}** | "
                 f"Dist: `{ruta_info['distancia_km']:.1f} km` | "
                 f"Costo: `${ruta_info['costo_estimado']:,.0f}` | "
                 f"Carga: `{ruta_info['total_demanda']:.0f} ({cap_pct:.1f}%)`")
        with st.expander(title):
            id_paradas = ruta_info.get('secuencia_paradas_ids', [])
            if not id_paradas:
                st.write("Sin paradas asignadas.")
                continue
            ruta_df = pd.DataFrame([paradas_dict.get(pid) for pid in id_paradas if pid in paradas_dict])
            st.dataframe(ruta_df[['id', 'demanda', 'lat', 'lon']], hide_index=True, use_container_width=True)
    st.markdown("---")

    st.subheader("📥 Descargar Informes")
    df_display = resumen_df[['vehiculo_id', 'total_demanda', 'capacidad_utilizada_pct', 'distancia_km', 'costo_estimado']].copy()
    informe_sheets = {"Resumen": df_display}
    for _, ruta in resumen_df.iterrows():
        sheet_name = f"Ruta {ruta['vehiculo_id']}"[:31]
        ruta_df = pd.DataFrame([paradas_dict.get(pid) for pid in ruta['secuencia_paradas_ids'] if pid in paradas_dict])
        informe_sheets[sheet_name] = ruta_df[['id', 'lat', 'lon', 'demanda']]
    col_excel, col_pdf = st.columns(2)
    with col_excel:
        excel_data = to_excel(informe_sheets)
        st.download_button(label="📥 Descargar (Excel)", data=excel_data,
                           file_name="informe_rutas.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           use_container_width=True)
    with col_pdf:
        html_report = generate_html_report(resumen_df, paradas_df)
        html_escaped = json.dumps(html_report)
        components.html(f"""
            <script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
            <button id="descargar_pdf" onclick="descargarPDF()">📄 Descargar (PDF)</button>
            <script>
                const informeHtml = {html_escaped};
                function descargarPDF() {{
                    const opt = {{ margin: 0.5, filename: 'informe_rutas.pdf', image: {{ type: 'jpeg', quality: 0.98 }},
                                   html2canvas: {{ scale: 2 }}, jsPDF: {{ unit: 'in', format: 'letter', orientation: 'portrait' }} }};
                    html2pdf().from(informeHtml).set(opt).save();
                }}
            </script>
            <style>
                #descargar_pdf {{ width: 100%; padding: 0.25rem 0.75rem; border-radius: 0.5rem;
                                  border: 1px solid rgba(49, 51, 63, 0.2); background-color: #FFFFFF;
                                  color: #31333F; cursor: pointer; line-height: 2.5; }}
                #descargar_pdf:hover {{ border-color: #FF4B4B; color: #FF4B4B; }}
            </style>
        """, height=50)
