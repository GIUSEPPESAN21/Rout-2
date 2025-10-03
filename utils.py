import numpy as np
from haversine import haversine

def create_distances(df):
    """
    Create a distance matrix from a dataframe with lat and lon columns.
    """
    locations = df[['lat', 'lon']].values
    num_locations = len(locations)
    distance_matrix = np.zeros((num_locations, num_locations))
    for i in range(num_locations):
        for j in range(num_locations):
            distance_matrix[i][j] = haversine(locations[i], locations[j])
    return distance_matrix.astype(int)
