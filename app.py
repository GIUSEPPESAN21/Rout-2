# app.py - Backend Profesional para Rout Now

import io
import math
import traceback
import uuid
import logging
import json
import os
from datetime import datetime, timedelta
from functools import lru_cache
from typing import List, Dict, Any, Tuple

from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import pandas as pd
import numpy as np
from python_tsp.heuristics import solve_tsp_simulated_annealing
from pydantic import BaseModel, ValidationError, Field

# ==============================================================================
# --- CONFIGURACIÓN DE LOGGING Y APLICACIÓN ---
# ==============================================================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# --- Constantes ---
COSTO_POR_KM_COP = 532
SESSION_EXPIRATION = timedelta(hours=2)
SESSIONS_DIR = "sessions" # Directorio para guardar las sesiones

# Crear directorio de sesiones si no existe
if not os.path.exists(SESSIONS_DIR):
    os.makedirs(SESSIONS_DIR)

# ==============================================================================
# --- MODELOS DE DATOS (VALIDACIÓN) ---
# ==============================================================================
class ParadaModel(BaseModel):
    id: str
    lat: float
    lon: float
    nombre: str
    pasajeros: int
    isDepot: bool = False
    tipo_zona: str = Field('N/A', alias='tipo_zona')

class VehiculoModel(BaseModel):
    id: str
    capacidad: int

class OptimizePayload(BaseModel):
    paradas: List[ParadaModel]
    vehiculos: List[VehiculoModel]

# ==============================================================================
# --- LÓGICA DE NEGOCIO ---
# ==============================================================================

class MemoryManager:
    """Gestiona los datos de sesión, ahora con persistencia en archivos."""
    def __init__(self, session_dir: str):
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.session_dir = session_dir

    def _get_session_path(self, session_id: str) -> str:
        return os.path.join(self.session_dir, f"{session_id}.json")

    def _save_session(self, session_id: str):
        """Guarda el estado de una sesión en un archivo JSON."""
        path = self._get_session_path(session_id)
        session_data = self.sessions.get(session_id, {})
        # Convertir datetime a string para que sea serializable en JSON
        if 'created_at' in session_data and isinstance(session_data['created_at'], datetime):
            session_data['created_at_str'] = session_data['created_at'].isoformat()
        
        # Crear una copia para no modificar el objeto en memoria
        data_to_save = session_data.copy()
        if 'created_at' in data_to_save:
            del data_to_save['created_at']

        with open(path, 'w') as f:
            json.dump(data_to_save, f, indent=4)

    def _load_session(self, session_id: str) -> bool:
        """Carga una sesión desde un archivo JSON si existe."""
        path = self._get_session_path(session_id)
        if os.path.exists(path):
            with open(path, 'r') as f:
                try:
                    session_data = json.load(f)
                    # Convertir el string de vuelta a datetime
                    if 'created_at_str' in session_data:
                        session_data['created_at'] = datetime.fromisoformat(session_data.pop('created_at_str'))
                    else:
                         session_data['created_at'] = datetime.now()

                    # Verificar si la sesión ha expirado
                    if datetime.now() - session_data['created_at'] > SESSION_EXPIRATION:
                        self.clear_session(session_id)
                        return False

                    self.sessions[session_id] = session_data
                    return True
                except (json.JSONDecodeError, KeyError):
                    return False
        return False

    def get_session(self, session_id: str = None) -> Tuple[str, Dict[str, Any]]:
        if session_id and session_id not in self.sessions:
            self._load_session(session_id)

        if not session_id or session_id not in self.sessions:
            session_id = str(uuid.uuid4())
            self.sessions[session_id] = {"created_at": datetime.now()}
            self._save_session(session_id)
            logging.info(f"Nueva sesión creada y guardada: {session_id}")
        
        return session_id, self.sessions[session_id]

    def update_session_data(self, session_id: str, key: str, value: Any):
        """Actualiza un dato en la sesión y lo guarda en disco."""
        if session_id in self.sessions:
            self.sessions[session_id][key] = value
            self._save_session(session_id)

    def clear_session(self, session_id: str):
        """Limpia una sesión de la memoria y elimina su archivo."""
        if session_id in self.sessions:
            del self.sessions[session_id]
        
        path = self._get_session_path(session_id)
        if os.path.exists(path):
            os.remove(path)
        logging.info(f"Sesión {session_id} limpiada y eliminada.")


class FileProcessor:
    """Procesa archivos CSV y Excel para extraer paradas."""
    def parse(self, file_stream: io.BytesIO, filename: str) -> List[Dict]:
        encodings_to_try = ['utf-8', 'latin-1', 'cp1252']
        content = file_stream.read()
        df = None
        for encoding in encodings_to_try:
            try:
                buffer = io.BytesIO(content)
                if filename.endswith('.csv'):
                    df = pd.read_csv(buffer, sep=None, engine='python', on_bad_lines='warn', encoding=encoding)
                elif filename.endswith(('.xls', '.xlsx')):
                    df = pd.read_excel(buffer)
                logging.info(f"Archivo leído exitosamente con codificación: {encoding}")
                break
            except Exception:
                logging.warning(f"Fallo al leer con codificación {encoding}, intentando la siguiente...")
                continue
        
        if df is None:
            raise ValueError("No se pudo decodificar el archivo con las codificaciones probadas.")

        df.columns = [str(c).lower().strip().replace(' ', '_') for c in df.columns]
        
        lat_col = next((c for c in df.columns if c in ['lat', 'latitude', 'latitud']), None)
        lon_col = next((c for c in df.columns if c in ['lon', 'lng', 'longitude', 'longitud']), None)
        if not lat_col or not lon_col: raise ValueError("Columnas de lat/lon no encontradas.")

        dem_col = next((c for c in df.columns if c in ['pasajeros', 'demanda', 'pax']), 'pasajeros')
        nom_col = next((c for c in df.columns if c in ['nombre', 'name']), 'nombre')
        zona_col = next((c for c in df.columns if c in ['tipo_zona', 'zona']), 'tipo_zona')

        paradas = []
        for i, row in df.iterrows():
            try:
                paradas.append({
                    "lat": float(row[lat_col]), "lon": float(row[lon_col]),
                    "nombre": str(row.get(nom_col, f"Parada {i+1}")),
                    "pasajeros": int(row.get(dem_col, 1)),
                    "tipo_zona": str(row.get(zona_col, 'N/A'))
                })
            except (ValueError, TypeError): continue
        return paradas

class OptimizationEngine:
    """Motor de optimización de rutas con algoritmo CVRP anti-sobrecupo."""
    @staticmethod
    @lru_cache(maxsize=None)
    def haversine(lat1, lon1, lat2, lon2):
        R = 6371000
        lat1_rad, lon1_rad, lat2_rad, lon2_rad = map(math.radians, [lat1, lon1, lat2, lon2])
        dlon, dlat = lon2_rad - lon1_rad, lat2_rad - lat1_rad
        a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
        return R * 2 * math.asin(math.sqrt(a))

    def run(self, paradas_models: List[ParadaModel], vehiculos_models: List[VehiculoModel]) -> List[Dict]:
        paradas = [p.model_dump() for p in paradas_models]
        vehiculos = [v.model_dump() for v in vehiculos_models]

        depot = next((p for p in paradas if p.get('isDepot')), None)
        if not depot: raise ValueError("Depósito no definido.")
        
        paradas_clientes_df = pd.DataFrame([p for p in paradas if not p.get('isDepot')])
        if paradas_clientes_df.empty: raise ValueError("No hay paradas de clientes para optimizar.")

        vehiculos_df = pd.DataFrame(vehiculos)
        if paradas_clientes_df['pasajeros'].sum() > vehiculos_df['capacidad'].sum():
            raise ValueError("Capacidad de flota insuficiente para la demanda total.")

        asignaciones = self._assign_stops_to_vehicles(paradas_clientes_df, vehiculos_df, depot)
        
        resultados = []
        paradas_dict = {p['id']: p for p in paradas}

        for vehiculo_id, parada_ids in asignaciones.items():
            if not parada_ids: continue
            
            ruta_optima_tsp = self._solve_tsp_for_route(parada_ids, depot, paradas_dict)
            
            vehiculo_info = vehiculos_df[vehiculos_df['id'] == vehiculo_id].iloc[0]
            total_pasajeros = paradas_clientes_df[paradas_clientes_df['id'].isin(parada_ids)]['pasajeros'].sum()
            capacidad_vehiculo = vehiculo_info['capacidad']
            utilizacion_pct = (total_pasajeros / capacidad_vehiculo) * 100 if capacidad_vehiculo > 0 else 0

            resultados.append({
                "vehiculo_id": vehiculo_id,
                "capacidad": int(capacidad_vehiculo),
                "total_pasajeros": int(total_pasajeros),
                "capacidad_utilizada_pct": utilizacion_pct,
                **ruta_optima_tsp
            })
        
        return sorted(resultados, key=lambda x: int(x['vehiculo_id'].split('_')[-1]))

    def _assign_stops_to_vehicles(self, paradas_df: pd.DataFrame, vehiculos_df: pd.DataFrame, depot: Dict) -> Dict:
        paradas_pendientes = paradas_df.copy().sort_values('pasajeros', ascending=False)
        asignaciones = {v_id: [] for v_id in vehiculos_df['id']}
        capacidad_restante = {row['id']: row['capacidad'] for _, row in vehiculos_df.iterrows()}
        
        for _, vehiculo in vehiculos_df.iterrows():
            vehiculo_id = vehiculo['id']
            last_pos = (depot['lat'], depot['lon'])
            
            while True:
                paradas_que_caben = paradas_pendientes[paradas_pendientes['pasajeros'] <= capacidad_restante[vehiculo_id]].copy()
                if paradas_que_caben.empty: break

                paradas_que_caben.loc[:, 'dist_a_last'] = paradas_que_caben.apply(
                    lambda row: self.haversine(last_pos[0], last_pos[1], row['lat'], row['lon']), axis=1
                )
                
                mejor_parada = paradas_que_caben.sort_values('dist_a_last').iloc[0]
                
                asignaciones[vehiculo_id].append(mejor_parada['id'])
                capacidad_restante[vehiculo_id] -= mejor_parada['pasajeros']
                paradas_pendientes = paradas_pendientes.drop(mejor_parada.name)
                last_pos = (mejor_parada['lat'], mejor_parada['lon'])
        
        if not paradas_pendientes.empty:
            logging.warning(f"{len(paradas_pendientes)} paradas no pudieron ser asignadas. Intente con más vehículos o de mayor capacidad.")

        return asignaciones

    def _solve_tsp_for_route(self, parada_ids: List[str], depot: Dict, paradas_dict: Dict) -> Dict:
        nodos_ids = [depot['id']] + parada_ids
        dist_matrix = np.array([[self.haversine(paradas_dict[i]['lat'], paradas_dict[i]['lon'], paradas_dict[j]['lat'], paradas_dict[j]['lon']) for j in nodos_ids] for i in nodos_ids])
        
        permutation, dist_m = solve_tsp_simulated_annealing(dist_matrix)
        
        nodos_ordenados = [nodos_ids[i] for i in permutation]
        start_idx = nodos_ordenados.index(depot['id'])
        secuencia_final_ids = nodos_ordenados[start_idx:] + nodos_ordenados[:start_idx]
        
        return {
            "secuencia_paradas_ids": [pid for pid in secuencia_final_ids if pid != depot['id']],
            "distancia_optima_m": dist_m,
            "costo_estimado_cop": (dist_m / 1000) * COSTO_POR_KM_COP
        }

class AIAnalyzer:
    """Simula un análisis de IA sobre los resultados."""
    def analyze(self, resultados: Dict):
        rutas = resultados.get('rutas', [])
        if not rutas: return {"titulo": "Análisis Rout-IA", "insights": ["No hay rutas para analizar."]}
        
        insights = [
            f"**Resumen:** Se planificaron **{len(rutas)} rutas**.",
            f"**Costo Total:** El costo operativo estimado es de **${sum(r['costo_estimado_cop'] for r in rutas):,.0f} COP**.",
            f"**Utilización Promedio:** {np.mean([r['capacidad_utilizada_pct'] for r in rutas]):.1f}%."
        ]
        if np.mean([r['capacidad_utilizada_pct'] for r in rutas]) < 65:
            insights.append("💡 **Sugerencia:** La flota parece subutilizada. Evalúe usar vehículos de menor capacidad o consolidar rutas si la geografía lo permite.")
        
        return { "titulo": "Análisis Logístico por Rout-IA", "insights": insights }

# --- INSTANCIAS DE CLASES ---
memory_manager = MemoryManager(SESSIONS_DIR)
file_processor = FileProcessor()
optimization_engine = OptimizationEngine()
ai_analyzer = AIAnalyzer()

# ==============================================================================
# --- RUTAS DE LA API (ENDPOINTS) ---
# ==============================================================================
@app.route('/')
def root():
    logging.info("Solicitud en la ruta raíz, sirviendo index.html.")
    return app.send_static_file('index.html')

@app.route('/api/session', methods=['GET'])
def get_new_session():
    session_id, _ = memory_manager.get_session()
    return jsonify({"session_id": session_id})

@app.route('/api/upload_paradas', methods=['POST'])
def upload_paradas():
    if 'file' not in request.files: return jsonify({"error": "No se encontró archivo"}), 400
    file = request.files['file']
    try:
        paradas = file_processor.parse(file.stream, file.filename)
        return jsonify(paradas), 200
    except Exception as e:
        return jsonify({"error": f"Error al procesar: {e}"}), 500

@app.route('/api/optimize', methods=['POST'])
def optimize():
    session_id, _ = memory_manager.get_session(request.headers.get('X-Session-ID'))
    try:
        payload = OptimizePayload(**request.get_json())
        resultados = optimization_engine.run(payload.paradas, payload.vehiculos)
        datos_a_guardar = {"rutas": resultados, "paradas": [p.model_dump() for p in payload.paradas]}
        memory_manager.update_session_data(session_id, 'resultados', datos_a_guardar)
        return jsonify({"rutas": resultados})
    except ValidationError as e:
        return jsonify({"error": f"Datos inválidos: {e.errors()}"}), 400
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logging.error(f"Error en optimización: {traceback.format_exc()}")
        return jsonify({"error": f"Error interno del servidor."}), 500

@app.route('/api/analyze', methods=['POST'])
def analyze():
    session_id, session_data = memory_manager.get_session(request.headers.get('X-Session-ID'))
    if not session_data.get('resultados'):
        return jsonify({"error": "No hay resultados para analizar. Por favor, optimice primero."}), 400
    analisis = ai_analyzer.analyze(session_data['resultados'])
    return jsonify(analisis)

@app.route('/api/export', methods=['GET'])
def export_results():
    session_id, session_data = memory_manager.get_session(request.headers.get('X-Session-ID'))
    resultados = session_data.get('resultados')
    if not resultados: return jsonify({"error": "No hay resultados para exportar. Por favor, optimice primero."}), 400

    try:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            all_paradas_dict = {p['id']: p for p in resultados['paradas']}
            depot = next((p for p in resultados['paradas'] if p.get('isDepot')), None)
            
            resumen_data = []
            for i, ruta in enumerate(resultados['rutas']):
                resumen_data.append({
                    "Ruta #": i + 1,
                    "Vehículo ID": ruta['vehiculo_id'].split('_')[-1],
                    "Paradas": len(ruta['secuencia_paradas_ids']),
                    "Pasajeros": ruta['total_pasajeros'],
                    "Utilización (%)": f"{ruta['capacidad_utilizada_pct']:.2f}",
                    "Distancia (km)": f"{ruta['distancia_optima_m'] / 1000:.2f}",
                    "Costo (COP)": f"{ruta['costo_estimado_cop']:,.0f}"
                })
            pd.DataFrame(resumen_data).to_excel(writer, sheet_name='Resumen de Rutas', index=False)

            for i, ruta in enumerate(resultados['rutas']):
                sheet_name = f"Ruta {i + 1} (Veh {ruta['vehiculo_id'].split('_')[-1]})"
                detalle_data = []
                if depot:
                    detalle_data.append({"Orden": "Inicio", "Nombre": depot.get('nombre'), "Pasajeros": "-", "Latitud": depot.get('lat'), "Longitud": depot.get('lon'), "Tipo Zona": depot.get('tipo_zona', 'N/A')})
                
                for j, parada_id in enumerate(ruta['secuencia_paradas_ids']):
                    parada = all_paradas_dict.get(parada_id, {})
                    detalle_data.append({
                        "Orden": j + 1, "Nombre": parada.get('nombre'), "Pasajeros": parada.get('pasajeros'),
                        "Latitud": parada.get('lat'), "Longitud": parada.get('lon'), "Tipo Zona": parada.get('tipo_zona', 'N/A')
                    })
                
                if depot:
                    detalle_data.append({"Orden": "Fin", "Nombre": depot.get('nombre'), "Pasajeros": "-", "Latitud": depot.get('lat'), "Longitud": depot.get('lon'), "Tipo Zona": depot.get('tipo_zona', 'N/A')})
                
                pd.DataFrame(detalle_data).to_excel(writer, sheet_name=sheet_name, index=False)

        output.seek(0)
        return send_file(output, as_attachment=True, download_name=f"RoutNow_Resultados.xlsx", mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    except Exception as e:
        logging.error(f"Error exportando: {traceback.format_exc()}")
        return jsonify({"error": "Error al generar el archivo Excel."}), 500

@app.route('/api/clear', methods=['POST'])
def clear_data():
    session_id, _ = memory_manager.get_session(request.headers.get('X-Session-ID'))
    memory_manager.clear_session(session_id)
    return jsonify({"message": "Sesión limpiada."}), 200

if __name__ == '__main__':
    print("="*60)
    print("🚀 SERVIDOR ROUT NOW v13.7 (FINAL CON SESIONES PERSISTENTES)")
    print(f"   URL: http://127.0.0.1:5000")
    print("="*60)
    app.run(host='0.0.0.0', port=5000, debug=True)
