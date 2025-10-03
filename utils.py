import numpy as np
from haversine import haversine

# --- INICIO DE LA CORRECCIÓN ---
# Se renombró la función de 'create_distances' a 'create_distance_matrix'
# para que coincida con la importación en solver.py.
def create_distance_matrix(df):
# --- FIN DE LA CORRECCIÓN ---
    """
    Crea una matriz de distancias entre todos los puntos geográficos
    utilizando la fórmula de Haversine.
    """
    locations = df[['lat', 'lon']].to_numpy()
    num_locations = len(locations)
    distance_matrix = np.zeros((num_locations, num_locations))

    for i in range(num_locations):
        for j in range(num_locations):
            if i != j:
                # La distancia se calcula en kilómetros (km)
                distance_matrix[i][j] = haversine(locations[i], locations[j])
    
    # OR-Tools espera distancias enteras, por lo que escalamos y convertimos.
    # Multiplicamos por 1000 para trabajar con metros y mantener precisión.
    return (distance_matrix * 1000).astype(int)
