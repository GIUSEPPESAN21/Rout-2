Rout-2: Aplicación de Optimización de Rutas con StreamlitEsta es una aplicación web robusta construida con Streamlit para resolver el Problema de Enrutamiento de Vehículos (VRP), diseñada para funcionar de manera fiable en **Streamlit Community Cloud**.

## Características Clave

-   **Lectura Segura de Archivos**: Soporta `.csv`, `.xlsx` y `.ods`, con validación automática de columnas y manejo de errores de codificación.
-   **Solver de Rutas Robusto**: Utiliza un solver avanzado (`python-tsp`) con un **fallback automático** a una heurística rápida si el primero falla, garantizando que siempre se obtenga una solución.
-   **Logging en la UI**: Un panel de logs integrado muestra información y errores de la sesión, facilitando el diagnóstico.
-   **CI con GitHub Actions**: Cada push ejecuta tests con `pytest` para asegurar la calidad del código.

## Despliegue en Streamlit Community Cloud

1.  **Haz un Fork de este Repositorio**.
2.  Inicia sesión en **[Streamlit Community Cloud](https://share.streamlit.io/)** con tu cuenta de GitHub.
3.  Haz clic en **"New app"** y selecciona tu repositorio `Rout-2`.
4.  Asegúrate de que la rama sea `main` y el archivo principal sea `streamlit_app.py`.
5.  Haz clic en **"Deploy!"**.

Streamlit se encargará del resto.
