import streamlit as st
import pydeck as pdk
import pandas as pd
import random

def get_random_color():
    return [random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)]

def create_map(df, solution):
    """
    Create a map with the routes.
    """
    if solution is None:
        return
    
    layer_list = []
    for i, route in enumerate(solution['routes']):
        route_df = df.iloc[route]
        path_data = [{
            "path": route_df[['lon', 'lat']].values.tolist(),
            "name": f"Route {i+1}",
            "color": get_random_color()
        }]
        layer = pdk.Layer(
            'PathLayer',
            data=path_data,
            pickable=True,
            get_color='color',
            width_scale=20,
            width_min_pixels=2,
            get_path='path',
            get_width=5
        )
        layer_list.append(layer)

    view_state = pdk.ViewState(
        latitude=df['lat'].mean(),
        longitude=df['lon'].mean(),
        zoom=11,
        pitch=50,
    )

    st.pydeck_chart(pdk.Deck(
        map_style='mapbox://styles/mapbox/light-v9',
        initial_view_state=view_state,
        layers=layer_list,
    ))
