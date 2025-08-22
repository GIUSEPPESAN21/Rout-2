Rout-2: Aplicación de Optimización de Rutas con Streamlit
Esta es una aplicación web construida con Streamlit para resolver el Problema de Enrutamiento de Vehículos (VRP). Permite a los usuarios cargar datos de paradas, configurar una flota de vehículos y visualizar las rutas optimizadas en un mapa interactivo.

Características
Carga de Datos Flexible: Sube archivos CSV o Excel con la información de las paradas.

Configuración Intuitiva: Ajusta el número de vehículos, sus capacidades y otros parámetros de la simulación.

Visualización Interactiva: Explora las rutas generadas en un mapa con Folium.

Resultados Detallados: Analiza métricas clave como distancia total, costos y utilización de la flota.

Exportación de Datos: Descarga los resultados en formatos CSV y GeoJSON para análisis posteriores.

Instalación y Ejecución Local
Sigue estos pasos para ejecutar la aplicación en tu máquina local.

Clona el repositorio:

git clone https://github.com/GIUSEPPESAN21/Rout-2.git
cd Rout-2

Crea y activa un entorno virtual:

python -m venv venv
# En Windows
venv\Scripts\activate
# En macOS/Linux
source venv/bin/activate

Instala las dependencias:

pip install -r requirements.txt

Ejecuta la aplicación de Streamlit:

streamlit run streamlit_app.py

La aplicación se abrirá automáticamente en tu navegador web.

Despliegue en la Nube
Streamlit Community Cloud
Sube tu código a un repositorio público de GitHub. Asegúrate de que streamlit_app.py y requirements.txt estén en la raíz del repositorio.

Inicia sesión en Streamlit Community Cloud.

Haz clic en "New app" y selecciona tu repositorio, la rama y el archivo principal (streamlit_app.py).

Haz clic en "Deploy!". Streamlit se encargará de instalar las dependencias y desplegar tu aplicación.

Hugging Face Spaces
Sube tu código a un repositorio de GitHub.

Inicia sesión en Hugging Face.

Ve a tu perfil y haz clic en "New Space".

Dale un nombre a tu Space, elige una licencia y selecciona "Streamlit" como el SDK del Space.

Elige la opción "Create from a GitHub repo" y selecciona tu repositorio.

Asegúrate de que el "App file" apunte a streamlit_app.py.

Haz clic en "Create Space". Hugging Face clonará tu repositorio y desplegará la aplicación. No se necesita un Dockerfile si usas la plantilla de Streamlit.
