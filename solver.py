from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
from utils import create_distance_matrix

# --- INICIO DE LA CORRECCIÓN ---
# Se renombró la función de 'solve' a 'solve_vrp' para que coincida
# con la importación en streamlit_app.py.
def solve_vrp(df, num_vehicles, vehicle_capacity):
# --- FIN DE LA CORRECCIÓN ---
    """
    Resuelve el Problema de Enrutamiento de Vehículos (VRP) utilizando OR-Tools.
    """
    # Crear el modelo de enrutamiento.
    manager = pywrapcp.RoutingIndexManager(len(df), num_vehicles, 0)
    routing = pywrapcp.RoutingModel(manager)

    # Crear la matriz de distancias.
    distance_matrix = create_distance_matrix(df)

    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return distance_matrix[from_node][to_node]

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # Añadir la restricción de capacidad.
    demands = df['demanda'].tolist()

    def demand_callback(from_index):
        from_node = manager.IndexToNode(from_index)
        return demands[from_node]

    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimension(
        demand_callback_index,
        0,  # Sin tiempo de holgura
        vehicle_capacity,
        True,  # Empezar acumulado desde cero
        'Capacity'
    )

    # Configurar los parámetros de búsqueda.
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )

    # Resolver el problema.
    assignment = routing.SolveWithParameters(search_parameters)

    if not assignment:
        return None

    # Extraer la solución.
    solution = {
        'routes': [],
        'route_distances': []
    }
    for vehicle_id in range(num_vehicles):
        index = routing.Start(vehicle_id)
        route = []
        route_distance = 0
        while not routing.IsEnd(index):
            node_index = manager.IndexToNode(index)
            route.append(node_index)
            previous_index = index
            index = assignment.Value(routing.NextVar(index))
            route_distance += routing.GetArcCostForVehicle(previous_index, index, vehicle_id)
        
        # Añadir el último nodo (depósito)
        route.append(manager.IndexToNode(index))
        
        if len(route) > 2: # Solo añadir rutas que visitan al menos un cliente
            solution['routes'].append(route)
            solution['route_distances'].append(route_distance)

    return solution
