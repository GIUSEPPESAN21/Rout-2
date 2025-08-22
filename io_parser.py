import pandas as pd
import streamlit as st
from io import BytesIO

REQUIRED_COLUMNS = ['id', 'lat', 'lon', 'demanda', 'is_depot']

def normalize_columns(df):
    """Normaliza los nombres de las columnas a un formato estándar."""
    cols = {col: col.lower().strip().replace(' ', '_') for col in df.columns}
    df = df.rename(columns=cols)
    return df

def validate_dataframe(df):
    """Valida que el DataFrame tenga las columnas y tipos de datos necesarios."""
    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Faltan columnas obligatorias: {', '.join(missing_cols)}")

    try:
        df['lat'] = pd.to_numeric(df['lat'])
        df['lon'] = pd.to_numeric(df['lon'])
        df['demanda'] = pd.to_numeric(df['demanda'])
        df['is_depot'] = df['is_depot'].astype(bool)
    except Exception as e:
        raise TypeError(f"Error en tipos de datos. lat/lon/demanda deben ser numéricos. Error: {e}")

    if df['is_depot'].sum() != 1:
        raise ValueError(f"Debe haber exactamente un depósito (una fila con 'is_depot' en True). Se encontraron {df['is_depot'].sum()}.")
        
    return df

@st.cache_data(show_spinner=False)
def safe_read_table(_uploaded_file):
    """Lee un archivo de forma segura, probando diferentes encodings y validando."""
    file_content = BytesIO(_uploaded_file.getvalue())
    file_name = _uploaded_file.name.lower()
    df = None
    
    encodings_to_try = ['utf-8', 'latin-1', 'cp1252']
    
    for encoding in encodings_to_try:
        try:
            file_content.seek(0) # Regresar al inicio del buffer
            if file_name.endswith('.csv'):
                df = pd.read_csv(file_content, sep=None, engine='python', encoding=encoding)
            elif file_name.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file_content, engine='openpyxl')
            elif file_name.endswith('.ods'):
                df = pd.read_excel(file_content, engine='odf')
            
            if df is not None:
                # Si la lectura fue exitosa, rompemos el bucle
                break
        except (UnicodeDecodeError, Exception):
            # Si falla el encoding, el bucle continuará con el siguiente
            continue
    
    if df is None:
        raise ValueError("No se pudo leer el archivo. Verifique el formato y la codificación (UTF-8, Latin-1).")

    df = normalize_columns(df)
    df = validate_dataframe(df)
    
    return df
