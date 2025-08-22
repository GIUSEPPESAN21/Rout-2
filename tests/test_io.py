import pandas as pd
from io import BytesIO
import pytest
from unittest.mock import MagicMock

# Añadir la ruta del proyecto para que pytest encuentre los módulos
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from io_parser import safe_read_table

def create_mock_file(content, name):
    """Crea un objeto de archivo simulado para los tests."""
    mock_file = MagicMock()
    mock_file.name = name
    mock_file.getvalue.return_value = content.encode('utf-8')
    return mock_file

def test_read_valid_csv():
    csv_content = "id,lat,lon,demanda,is_depot\ndepot1,4.5,-74.1,0,True\nstop1,4.6,-74.2,10,False"
    mock_file = create_mock_file(csv_content, "valid.csv")
    df = safe_read_table(mock_file)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert 'lat' in df.columns

def test_read_excel_file():
    # Crear un archivo Excel en memoria
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        pd.DataFrame({
            'ID': ['depot1', 'stop1'], 'Lat': [4.5, 4.6], 'Lon': [-74.1, -74.2],
            'Demanda': [0, 10], 'IS_DEPOT': [True, False]
        }).to_excel(writer, index=False)
    output.seek(0)
    
    mock_file = MagicMock()
    mock_file.name = "test.xlsx"
    mock_file.getvalue.return_value = output.read()

    df = safe_read_table(mock_file)
    assert len(df) == 2
    assert 'is_depot' in df.columns

def test_missing_columns_raises_error():
    csv_content = "id,lat,demanda\ndepot1,4.5,0"
    mock_file = create_mock_file(csv_content, "missing_cols.csv")
    with pytest.raises(ValueError, match="Faltan columnas obligatorias: lon, is_depot"):
        safe_read_table(mock_file)

def test_no_depot_raises_error():
    csv_content = "id,lat,lon,demanda,is_depot\nstop1,4.6,-74.2,10,False"
    mock_file = create_mock_file(csv_content, "no_depot.csv")
    with pytest.raises(ValueError, match="Debe haber exactamente un depósito"):
        safe_read_table(mock_file)
