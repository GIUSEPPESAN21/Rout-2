import streamlit as st
import pydeck as pdk
import pandas as pd
import random

def get_random_color():
    """Genera un color RGB aleatorio."""
    return [random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)]

# --- INICIO DE LA CORRECCIÓN ---
# Se renombró la función de 'create_map' a 'get_map' para que coincida
# con la importación en streamlit_app.py.
def get_map(df, solution):
# --- FIN DE LA CORRECCIÓN ---
    """
    Crea y muestra un mapa de PyDeck con las rutas de los vehículos.
    """
    if solution is None or not solution['routes']:
        st.pydeck_chart(pdk.Deck(
            map_style='mapbox://styles/mapbox/light-v9',
            initial_view_state=pdk.ViewState(
                latitude=df['lat'].mean(),
                longitude=df['lon'].mean(),
                zoom=10,
                pitch=50,
            ),
            layers=[],
        ))
        return

    route_layers = []
    for i, route_indices in enumerate(solution['routes']):
        route_df = df.iloc[route_indices]
        path_data = [{
            "path": route_df[['lon', 'lat']].values.tolist(),
            "name": f"Ruta {i+1}",
            "color": get_random_color()
        }]
        
        route_layers.append(pdk.Layer(
            'PathLayer',
            data=path_data,
            pickable=True,
            get_color='color',
            width_scale=20,
            width_min_pixels=2,
            get_path='path',
            get_width=5
        ))

    # Capa para los puntos de entrega (clientes)
    client_df = df.iloc[1:] # Excluir el depósito
    scatter_layer = pdk.Layer(
        'ScatterplotLayer',
        data=client_df,
        get_position='[lon, lat]',
        get_color='[200, 30, 0, 160]',
        get_radius=100,
        pickable=True,
        auto_highlight=True
    )

    # Capa para el depósito
    depot_df = df.iloc[[0]]
    depot_layer = pdk.Layer(
        'ScatterplotLayer',
        data=depot_df,
        get_position='[lon, lat]',
        get_color='[0, 0, 255, 200]', # Azul para el depósito
        get_radius=200,
        pickable=True
    )
    
    view_state = pdk.ViewState(
        latitude=df['lat'].mean(),
        longitude=df['lon'].mean(),
        zoom=10,
        pitch=50,
    )

    tooltip = {
        "html": "<b>{nombre}</b><br/>Demanda: {demanda}",
        "style": {
            "backgroundColor": "steelblue",
            "color": "white"
        }
    }

    st.pydeck_chart(pdk.Deck(
        map_style='mapbox://styles/mapbox/light-v9',
        initial_view_state=view_state,
        layers=[scatter_layer, depot_layer] + route_layers,
        tooltip=tooltip
    ))
