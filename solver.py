    import numpy as np
    import pandas as pd
    import math
    from python_tsp.heuristics import solve_tsp_simulated_annealing
    from utils import get_logger
    
    logger = get_logger()
    
    def haversine(lat1, lon1, lat2, lon2):
        R = 6371  # Radio de la Tierra en km
        lat1_rad, lon1_rad, lat2_rad, lon2_rad = map(math.radians, [lat1, lon1, lat2, lon2])
        dlon, dlat = lon2_rad - lon1_rad, lat2_rad - lat1_rad
        a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
        return R * 2 * math.asin(math.sqrt(a))
    
    def create_distance_matrix(paradas_df):
        paradas_dict = paradas_df.to_dict('records')
        ids = [p['id'] for p in paradas_dict]
        n = len(paradas_dict)
        dist_matrix = np.zeros((n, n))
        for i in range(n):
            for j in range(i, n):
                dist = haversine(paradas_dict[i]['lat'], paradas_dict[i]['lon'], paradas_dict[j]['lat'], paradas_dict[j]['lon'])
                dist_matrix[i, j] = dist_matrix[j, i] = dist
        return dist_matrix, ids
    
    def nearest_neighbor_solver(dist_matrix):
        num_nodos = len(dist_matrix)
        if num_nodos == 0: return [], 0
        visitados, ruta, distancia_total = [False] * num_nodos, [0], 0
        visitados[0], actual = True, 0
        for _ in range(num_nodos - 1):
            siguiente, dist_min = -1, float('inf')
            for i in range(num_nodos):
                if not visitados[i] and dist_matrix[actual][i] < dist_min:
                    dist_min, siguiente = dist_matrix[actual][i], i
            if siguiente != -1:
                ruta.append(siguiente)
                visitados[siguiente], distancia_total, actual = True, distancia_total + dist_min, siguiente
        distancia_total += dist_matrix[actual][0]
        return ruta, distancia_total
    
    def solve_tsp_with_fallback(dist_matrix, random_seed):
        num_nodos = len(dist_matrix)
        if num_nodos <= 2:
            return list(range(num_nodos)), np.sum(dist_matrix) if num_nodos == 2 else 0
        try:
            logger.info(f"Intentando solver avanzado para {num_nodos} nodos...")
            if np.isnan(dist_matrix).any() or np.isinf(dist_matrix).any():
                raise ValueError("Matriz de distancia contiene NaN/Inf.")
            permutation, distance = solve_tsp_simulated_annealing(dist_matrix, seed=random_seed)
            logger.info("Solver avanzado completado con éxito.")
            return permutation, distance
        except (StopIteration, ValueError) as e:
            logger.warning(f"Solver avanzado falló ({type(e).__name__}). Ejecutando fallback (Nearest Neighbor).")
            return nearest_neighbor_solver(dist_matrix)
    
    def assign_stops_to_vehicles(paradas_df, vehiculos_df, depot):
        paradas_pendientes = paradas_df.copy().sort_values('demanda', ascending=False)
        asignaciones = {v_id: [] for v_id in vehiculos_df['id']}
        capacidad_restante = {row['id']: row['capacidad'] for _, row in vehiculos_df.iterrows()}
        for _, vehiculo in vehiculos_df.iterrows():
            vehiculo_id = vehiculo['id']
            last_pos = (depot['lat'], depot['lon'])
            while True:
                paradas_que_caben = paradas_pendientes[paradas_pendientes['demanda'] <= capacidad_restante[vehiculo_id]].copy()
                if paradas_que_caben.empty: break
                paradas_que_caben['dist_a_last'] = paradas_que_caben.apply(lambda r: haversine(last_pos[0], last_pos[1], r['lat'], r['lon']), axis=1)
                mejor_parada = paradas_que_caben.sort_values('dist_a_last').iloc[0]
                asignaciones[vehiculo_id].append(mejor_parada['id'])
                capacidad_restante[vehiculo_id] -= mejor_parada['demanda']
                paradas_pendientes = paradas_pendientes.drop(mejor_parada.name)
                last_pos = (mejor_parada['lat'], mejor_parada['lon'])
        return asignaciones
    
    def run_optimization(paradas_df, vehiculos_df, costo_km, velocidad_kmh, random_seed, force_fallback=False):
        logger.info("Iniciando optimización de rutas.")
        depot = paradas_df[paradas_df['is_depot']].iloc[0].to_dict()
        paradas_clientes_df = paradas_df[~paradas_df['is_depot']]
        asignaciones = assign_stops_to_vehicles(paradas_clientes_df, vehiculos_df, depot)
        resultados = []
        paradas_dict = {p['id']: p for _, p in paradas_df.iterrows()}
        for vehiculo_id, parada_ids in asignaciones.items():
            if not parada_ids: continue
            nodos_ruta_ids = [depot['id']] + parada_ids
            nodos_ruta_df = paradas_df[paradas_df['id'].isin(nodos_ruta_ids)].set_index('id').loc[nodos_ruta_ids].reset_index()
            dist_matrix, ordered_ids = create_distance_matrix(nodos_ruta_df)
            if force_fallback:
                logger.info(f"Forzando fallback para vehículo {vehiculo_id}.")
                permutation, dist_km = nearest_neighbor_solver(dist_matrix)
            else:
                permutation, dist_km = solve_tsp_with_fallback(dist_matrix, random_seed)
            nodos_ordenados = [ordered_ids[i] for i in permutation]
            start_idx = nodos_ordenados.index(depot['id'])
            secuencia_final_ids = nodos_ordenados[start_idx:] + nodos_ordenados[:start_idx]
            total_demanda = paradas_clientes_df[paradas_clientes_df['id'].isin(parada_ids)]['demanda'].sum()
            vehiculo_info = vehiculos_df[vehiculos_df['id'] == vehiculo_id].iloc[0]
            resultados.append({
                "vehiculo_id": vehiculo_id, "capacidad": int(vehiculo_info['capacidad']), "total_demanda": int(total_demanda),
                "capacidad_utilizada_pct": (total_demanda / vehiculo_info['capacidad']) * 100, "distancia_km": dist_km,
                "costo_estimado": dist_km * costo_km, "tiempo_estimado_h": dist_km / velocidad_kmh if velocidad_kmh > 0 else 0,
                "secuencia_paradas_ids": [pid for pid in secuencia_final_ids if pid != depot['id']]
            })
        logger.info(f"Optimización finalizada. Se generaron {len(resultados)} rutas.")
        return sorted(resultados, key=lambda x: int(str(x['vehiculo_id']).split('_')[-1]))
    
