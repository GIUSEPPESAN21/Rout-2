import streamlit as st
import pandas as pd
import sys
import os

# Añadir el directorio actual al path de Python para asegurar que los módulos locales 
# (solver, io_parser, etc.) se encuentren durante la importación.
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from io_parser import parse_input_file
from solver import solve_vrp
from visualization import get_map

def main():
    st.set_page_config(page_title="Optimizador de Rutas VRP", layout="wide")
    
    st.title("🚚 Optimizador de Rutas (VRP)")
    st.write(
        "Esta herramienta resuelve el Problema de Enrutamiento de Vehículos (VRP) para encontrar las rutas más eficientes. "
        "Sube un archivo CSV con tus puntos de entrega."
    )

    # --- Sidebar para Carga de Archivos y Parámetros ---
    with st.sidebar:
        st.header("Configuración")
        
        uploaded_file = st.file_uploader(
            "Cargar archivo de clientes (CSV)",
            type=["csv"],
            help="El archivo debe tener las columnas 'lat', 'lon' y 'demanda' (o 'pasajeros'). El separador debe ser punto y coma ';'."
        )

        num_vehicles = st.number_input("Número de vehículos", min_value=1, value=4)
        vehicle_capacity = st.number_input("Capacidad por vehículo", min_value=1, value=100)
        
        st.info("El primer punto en el archivo CSV se considerará el depósito inicial.")

    # --- Área Principal para Resultados ---
    if uploaded_file is not None:
        try:
            # Usar la función de parseo mejorada de io_parser.py
            df = parse_input_file(uploaded_file)

            if df is not None and not df.empty:
                st.header("Datos Cargados")
                st.dataframe(df)

                if st.button("Resolver Rutas"):
                    with st.spinner("Calculando las rutas óptimas..."):
                        try:
                            solution = solve_vrp(df, num_vehicles, vehicle_capacity)
                            if solution:
                                st.header("Resultados de la Optimización")
                                
                                # Mostrar el mapa con las rutas
                                st.pydeck_chart(get_map(df, solution))

                                # Mostrar detalles de las rutas
                                st.subheader("Detalle de las Rutas")
                                total_distance = 0
                                for i, route in enumerate(solution['routes']):
                                    route_distance = solution['route_distances'][i]
                                    total_distance += route_distance
                                    st.write(f"**Vehículo {i + 1}:**")
                                    st.write(f"  - Recorrido: {' -> '.join(map(str, route))}")
                                    st.write(f"  - Distancia: {route_distance:.2f} km")
                                st.metric("Distancia Total Recorrida", f"{total_distance:.2f} km")

                            else:
                                st.error("No se encontró una solución. Prueba a aumentar el número de vehículos o la capacidad.")
                        
                        except Exception as e:
                            st.error(f"Ocurrió un error durante la resolución del problema: {e}")

        except (ValueError, RuntimeError) as e:
            # Mostrar errores de parseo o validación de forma clara
            st.error(f"Error al procesar el archivo: {e}")
            st.image("image_d21a22.png", caption="Error en el formato de datos.", use_column_width=True)

    else:
        st.info("Por favor, carga un archivo CSV para comenzar.")

if __name__ == "__main__":
    main()
