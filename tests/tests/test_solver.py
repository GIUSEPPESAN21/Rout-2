import numpy as np
import pytest

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from solver import solve_tsp_with_fallback, nearest_neighbor_solver

def test_fallback_for_small_problem():
    dist_matrix = np.array([[0, 1], [1, 0]])
    ruta, dist = solve_tsp_with_fallback(dist_matrix, 42)
    assert len(ruta) == 2
    assert dist == 2.0 # 1 (0->1) + 1 (1->0)

def test_nearest_neighbor():
    dist_matrix = np.array([
        [0, 2, 9, 10],
        [1, 0, 6, 4],
        [15, 7, 0, 8],
        [6, 3, 12, 0]
    ])
    # Ruta esperada NN desde 0: 0 -> 1 -> 3 -> 2 -> 0
    # Distancia: 2 + 4 + 8 + 15 = 29
    ruta, dist = nearest_neighbor_solver(dist_matrix)
    assert dist == 29
    assert ruta == [0, 1, 3, 2]

def test_solver_handles_nan_matrix_by_fallback():
    dist_matrix = np.array([[0, 1], [1, np.nan]])
    # El solver avanzado debería fallar, activando el fallback
    # El fallback no maneja NaNs, pero el test es para el wrapper
    with pytest.raises(ValueError):
         # El wrapper debería lanzar un error antes de llamar al fallback si hay NaN
         solve_tsp_with_fallback(dist_matrix, 42)
