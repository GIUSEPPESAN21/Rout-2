import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from io import BytesIO
import json
import streamlit.components.v1 as components

# Las funciones to_excel, generate_html_report y render_map se mantienen EXACTAMENTE IGUALES
def to_excel(df_dict):
    # ... (código original sin cambios) ...
# ... (código de generate_html_report sin cambios) ...
# ... (código de render_map sin cambios) ...

def render_results_section(resultados, paradas_df):
    """
    Muestra la sección de resultados con el nuevo formato inspirado en la app ACO.
    """
    if not resultados:
        st.info("No hay resultados para mostrar.")
        return

    resumen_df = pd.DataFrame(resultados)
    
    # --- NUEVO: Resumen Ejecutivo con Métricas ---
    st.subheader("📈 Resumen Ejecutivo")
    total_distancia = resumen_df['distancia_km'].sum()
    total_costo = resumen_df['costo_estimado'].sum()
    total_tiempo_h = resumen_df['tiempo_estimado_h'].sum()
    
    def format_duration(hours):
        h = int(hours)
        m = int((hours - h) * 60)
        return f"{h}h {m}min"

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Vehículos Utilizados", f"{len(resumen_df)}")
    m2.metric("Distancia Total", f"{total_distancia:.2f} km")
    m3.metric("Costo Total", f"${total_costo:,.2f}")
    m4.metric("Tiempo Total de Operación", f"{format_duration(total_tiempo_h)}")
    
    st.markdown("---")
    
    # --- NUEVO: Detalles por Ruta en Expanders ---
    st.subheader("📋 Detalles por Ruta")
    
    paradas_dict = {p['id']: p for _, p in paradas_df.iterrows()}

    for i, ruta_info in enumerate(resumen_df.to_dict('records')):
        capacidad_pct = ruta_info.get('capacidad_utilizada_pct', 0)
        
        expander_title = (
            f"**{ruta_info['vehiculo_id']}** | "
            f"Distancia: `{ruta_info['distancia_km']:.1f} km` | "
            f"Costo: `${ruta_info['costo_estimado']:,.0f}` | "
            f"Carga: `{ruta_info['total_demanda']:.0f} ({capacidad_pct:.1f}%)`"
        )
        with st.expander(expander_title):
            id_paradas_ruta = ruta_info.get('secuencia_paradas_ids', [])
            if not id_paradas_ruta:
                st.write("Esta ruta no tiene paradas asignadas.")
                continue

            # Construir el DataFrame para la tabla de la ruta
            ruta_df = pd.DataFrame([paradas_dict[pid] for pid in id_paradas_ruta])
            st.dataframe(
                ruta_df[['id', 'demanda', 'lat', 'lon']],
                hide_index=True,
                use_container_width=True
            )

    st.markdown("---")
    st.subheader("📥 Descargar Informes Completos")
    
    # --- Lógica de Descarga Original Mantenida ---
    df_display = resumen_df[['vehiculo_id', 'total_demanda', 'capacidad_utilizada_pct', 'distancia_km', 'costo_estimado']].copy()
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
            mime="application/vnd.openxmlformats-officedocument.spreadsheet.mlsheet", use_container_width=True)
    with col_pdf:
        # Tu componente de descarga de PDF se mantiene
        html_report = generate_html_report(resumen_df, paradas_df)
        html_escaped = json.dumps(html_report)
        components.html(f"""
            <script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
            <button id="descargar_pdf" onclick="descargarPDF()">📄 Descargar Informe (PDF)</button>
            <script>
                // ... (tu script de JS para el PDF sin cambios) ...
            </script>
            <style>
                // ... (tus estilos CSS para el botón sin cambios) ...
            </style>
        """, height=50)
