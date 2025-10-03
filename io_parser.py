import pandas as pd
import streamlit as st
from io import StringIO

def parse_input_file(uploaded_file):
    """
    Analiza un archivo CSV cargado, lo limpia y lo convierte en un DataFrame de Pandas.
    Esta versión está diseñada para manejar delimitadores de punto y coma,
    comas como separadores decimales y espacios extra en los datos numéricos.
    """
    if uploaded_file is None:
        return None

    try:
        # Decodificar el archivo cargado a una cadena de texto
        string_data = uploaded_file.getvalue().decode('utf-8')
        
        # Leer los datos usando el punto y coma como delimitador
        df = pd.read_csv(StringIO(string_data), delimiter=';')

        # Renombrar columnas para estandarizar (de 'pasajeros' a 'demanda')
        if 'pasajeros' in df.columns:
            df.rename(columns={'pasajeros': 'demanda'}, inplace=True)

        # Validar que las columnas necesarias existan
        required_cols = ['lat', 'lon', 'demanda']
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Error: La columna requerida '{col}' no se encuentra en el archivo.")

        # --- INICIO DE LA CORRECCIÓN ---
        # Limpiar y convertir las columnas numéricas
        for col in required_cols:
            # 1. Asegurarse de que la columna sea de tipo string para poder limpiarla
            df[col] = df[col].astype(str)
            # 2. Reemplazar la coma decimal por un punto
            df[col] = df[col].str.replace(',', '.', regex=False)
            # 3. Eliminar espacios en blanco al inicio y al final (incluyendo espacios de no separación)
            df[col] = df[col].str.strip()
            # 4. Convertir a tipo numérico. Si algo falla, se convierte en NaN (Not a Number)
            df[col] = pd.to_numeric(df[col], errors='coerce')
        # --- FIN DE LA CORRECCIÓN ---

        # Verificar si alguna conversión falló y ahora hay valores nulos
        if df[required_cols].isnull().values.any():
            st.warning("Se encontraron valores no numéricos en las columnas 'lat', 'lon' o 'demanda' después de la limpieza. Esas filas serán ignoradas.")
            df.dropna(subset=required_cols, inplace=True)

        # Asegurarse de que los tipos de datos finales sean correctos
        df = df.astype({'lat': float, 'lon': float, 'demanda': float})

        return df

    except ValueError as ve:
        # Propagar errores de validación para que la app principal los muestre
        raise ve
    except Exception as e:
        # Capturar otros posibles errores de lectura o procesamiento
        raise RuntimeError(f"No se pudo procesar el archivo. Verifique que sea un CSV válido con delimitador ';'. Error original: {e}")
