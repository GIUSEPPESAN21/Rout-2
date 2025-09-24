import pandas as pd
import streamlit as st
from io import BytesIO

def safe_read_table(_uploaded_file):
    """
    Lee un archivo de forma inteligente, detectando separador y mapeando columnas.
    MODIFICADO: Ya no requiere ni genera la columna 'is_depot'.
    El depósito se añade manualmente en la app principal.
    """
    file_content = BytesIO(_uploaded_file.getvalue())
    file_name = _uploaded_file.name.lower()
    df = None

    # --- 1. Leer el archivo de forma robusta (sin cambios) ---
    try:
        if file_name.endswith('.csv'):
            try:
                df = pd.read_csv(file_content, sep=None, engine='python', encoding='utf-8')
            except Exception:
                file_content.seek(0)
                df = pd.read_csv(file_content, sep=';', engine='python', encoding='latin-1')
        elif file_name.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file_content, engine='openpyxl')
        elif file_name.endswith('.ods'):
            df = pd.read_excel(file_content, engine='odf')
        else:
            raise ValueError("Formato de archivo no soportado.")
    except Exception as e:
        raise ValueError(f"No se pudo leer el archivo. Error: {e}")

    if df is None or df.empty:
        raise ValueError("El archivo está vacío o no se pudo leer.")

    # --- 2. Normalizar y Mapear Columnas (sin cambios) ---
    df.columns = [str(col).lower().strip().replace(' ', '_') for col in df.columns]
    column_map = {
        "pasajeros": "demanda",
        "nombre": "id"
    }
    df.rename(columns=column_map, inplace=True)

    # --- 3. Validar Columnas Esenciales (sin 'is_depot') ---
    # La columna 'is_depot' ya no es necesaria aquí.
    required_final_cols = ['id', 'lat', 'lon', 'demanda']
    missing_cols = [col for col in required_final_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Faltan columnas esenciales en el archivo: {', '.join(missing_cols)}")

    # Asegurarse de que 'is_depot' no cause problemas si viene en el archivo
    if 'is_depot' in df.columns:
        st.warning("La columna 'is_depot' en el archivo será ignorada. El depósito se define en el mapa.")
        df.drop(columns=['is_depot'], inplace=True)
    
    # Se añade la columna 'is_depot' como False para todas las filas (clientes)
    df['is_depot'] = False

    # --- 4. Validar Tipos de Datos (sin cambios en esta parte) ---
    try:
        df['lat'] = pd.to_numeric(df['lat'])
        df['lon'] = pd.to_numeric(df['lon'])
        df['demanda'] = pd.to_numeric(df['demanda'])
    except Exception as e:
        raise TypeError(f"Error en los tipos de datos. 'lat', 'lon' y 'demanda' deben ser números. Error: {e}")

    # La validación de que haya un solo depósito se elimina, ya que se gestiona en la UI.
        
    return df
