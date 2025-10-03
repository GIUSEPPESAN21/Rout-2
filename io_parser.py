import pandas as pd
import streamlit as st

def parse_input_file(uploaded_file):
    """
    Parsea el archivo de entrada (CSV o Excel) y lo convierte en un DataFrame.
    El DataFrame debe tener las columnas: 'lat', 'lon' y 'demanda'.
    """
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        elif uploaded_file.name.endswith('.xlsx'):
            df = pd.read_excel(uploaded_file)
        else:
            raise ValueError("Formato de archivo no soportado. Use CSV o XLSX.")

        # Asegurarse de que las columnas requeridas existan
        required_columns = ['lat', 'lon', 'demanda']
        if not all(col in df.columns for col in required_columns):
            raise ValueError(f"El archivo debe contener las columnas: {', '.join(required_columns)}")

        # Convertir a tipos de datos numéricos
        for col in required_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Verificar si hay valores nulos después de la conversión
        if df[required_columns].isnull().values.any():
            raise ValueError("Error en los tipos de datos. 'lat', 'lon' y 'demanda' deben ser números.")

        return df

    except Exception as e:
        st.error(f"Error al leer el archivo: {e}")
        return None
