import streamlit as st
from io_parser import parse_input_file
from solver import solve_vrp
from visualization import get_map

def main():
    st.set_page_config(page_title="VRP Solver", layout="wide")
    st.title("Vehicle Routing Problem (VRP) Solver")

    st.sidebar.header("Configuración")
    uploaded_file = st.sidebar.file_uploader("Cargar archivo de entrada (CSV o Excel)", type=["csv", "xlsx"])
    num_vehicles = st.sidebar.number_input("Número de vehículos", min_value=1, value=5)
    vehicle_capacity = st.sidebar.number_input("Capacidad del vehículo", min_value=1, value=100)

    if uploaded_file is not None:
        try:
            df = parse_input_file(uploaded_file)
            st.subheader("Datos de Entrada")
            st.dataframe(df)

            if st.sidebar.button("Resolver VRP"):
                with st.spinner("Resolviendo..."):
                    solution = solve_vrp(df, num_vehicles, vehicle_capacity)
                
                if solution:
                    st.subheader("Solución Encontrada")
                    st.success("¡Optimización completada!")
                    
                    st.write("Rutas:")
                    for i, route in enumerate(solution['routes']):
                        st.write(f"Vehículo {i+1}: {route}")
                    
                    st.subheader("Visualización del Mapa")
                    get_map(df, solution)
                else:
                    st.error("No se pudo encontrar una solución.")
        
        except Exception as e:
            st.error(f"Error al procesar: {e}")

if __name__ == "__main__":
    main()
