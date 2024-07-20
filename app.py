# Para crear el requirements.txt ejecutamos 
# pipreqs --encoding=utf8 --force

# Primera Carga a Github
# git init
# git add .
# git remote add origin https://github.com/nicoig/eco-gpt.git
# git commit -m "Initial commit"
# git push -u origin master

# Actualizar Repo de Github
# git add .
# git commit -m "Se actualizan las variables de entorno"
# git push origin master

# En Render
# agregar en variables de entorno
# PYTHON_VERSION = 3.9.12

# git remote set-url origin https://github.com/nicoig/eco-gpt.git
# git remote -v
# git push -u origin main

import streamlit as st
import sqlite3
import base64
from openai import OpenAI
from dotenv import load_dotenv, find_dotenv
import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from oauthlib.oauth2.rfc6749.errors import InvalidGrantError
from datetime import datetime

# Configuración inicial
st.set_page_config(page_title="EcoGPT - Asistente de Reciclaje IA", layout="wide")
load_dotenv(find_dotenv())

# CSS personalizado
st.markdown(
    """
    <style>
    .menu-container {
        display: flex;
        justify-content: flex-end;
        padding: 10px;
        background-color: #81B622;
    }
    .menu-item {
        margin-left: 20px;
        text-decoration: none;
        color: white;
        font-weight: bold;
    }
    .css-18e3th9 {
        background-color: #81B622;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Muestra la imagen con un tamaño específico
st.image('img/ecogpt_green.png', use_column_width=False, width=300)

# Inicializa st.session_state.user si aún no está definido
if 'user' not in st.session_state:
    st.session_state.user = None

# Configuración de Google OAuth
CLIENT_CONFIG = {
    "web": {
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
}
SCOPES = ['https://www.googleapis.com/auth/userinfo.email', 'https://www.googleapis.com/auth/userinfo.profile', 'openid']

# Inicialización de clientes y conexiones
cliente_openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
conn = sqlite3.connect('users.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users
             (email TEXT PRIMARY KEY, password TEXT, google_id TEXT)''')

# Verificar si la columna google_id existe, si no, añadirla
c.execute("PRAGMA table_info(users)")
columns = [column[1] for column in c.fetchall()]
if 'google_id' not in columns:
    c.execute("ALTER TABLE users ADD COLUMN google_id TEXT")

# Crear tabla para almacenar el historial de reciclaje
c.execute('''CREATE TABLE IF NOT EXISTS reciclaje
             (email TEXT, descripcion TEXT, fecha TEXT)''')
conn.commit()

# Funciones de utilidad
def codificar_imagen(archivo_imagen):
    return base64.b64encode(archivo_imagen.read()).decode('utf-8')

def texto_a_voz(texto):
    try:
        respuesta = cliente_openai.audio.speech.create(
            model="tts-1", voice="alloy", input=texto
        )
        return respuesta.content, None
    except Exception as error:
        return None, f"Error al generar audio: {error}"

def obtener_contenido_audio(contenido_audio):
    audio_base64 = base64.b64encode(contenido_audio).decode('utf-8')
    return f'data:audio/mp3;base64,{audio_base64}'

def verificar_usuario_google(google_id, email):
    c.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = c.fetchone()
    
    if user is None:
        c.execute("INSERT INTO users (email, google_id) VALUES (?, ?)", (email, google_id))
    else:
        c.execute("UPDATE users SET google_id = ? WHERE email = ?", (google_id, email))
    
    conn.commit()
    return email

def registrar_reciclaje(email, descripcion):
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO reciclaje (email, descripcion, fecha) VALUES (?, ?, ?)", (email, descripcion, fecha))
    conn.commit()

def obtener_historial_reciclaje(email):
    c.execute("SELECT descripcion, fecha FROM reciclaje WHERE email = ?", (email,))
    return c.fetchall()

def autoplay_audio(file_path: str):
    with open(file_path, "rb") as f:
        data = f.read()
        b64 = base64.b64encode(data).decode()
        md = f"""
            <audio autoplay="true">
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
            </audio>
            """
        st.markdown(md, unsafe_allow_html=True)

# Función para crear el menú superior
def crear_menu_superior():
    menu = """
    <style>
    .menu-container {
        display: flex;
        justify-content: flex-end;
        padding: 10px;
        background-color: #81B622;
    }
    .menu-item {
        margin-left: 20px;
        text-decoration: none;
        color: white !important;  /* Asegura que el color de las letras sea blanco */
        font-weight: bold;
    }
    </style>
    <div class="menu-container">
        <a href="/" class="menu-item">Inicio</a>
        <a href="/mi-cuenta" class="menu-item">Mi Cuenta</a>
        <a href="#" onclick="logout()" class="menu-item">Cerrar Sesión</a>
    </div>
    <script>
    function logout() {
        localStorage.clear();
        window.location.href = '/';
    }
    </script>
    """
    st.markdown(menu, unsafe_allow_html=True)


# Página principal
def main_page():
    st.write(f"Sesión iniciada como: {st.session_state.user}")
    st.write("Sube una foto del producto para recibir consejos de reciclaje.")

    archivo_subido = st.file_uploader("Sube una imagen del producto a reciclar", type=["jpg", "png", "jpeg"])
    if archivo_subido:
        st.image(archivo_subido, caption='Vista previa', width=300)
        if st.button("Analizar Producto"):
            with st.spinner('Analizando...'):
                imagen = codificar_imagen(archivo_subido)
                respuesta = cliente_openai.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "Eres un experto en reciclaje y análisis de materiales."},
                        {"role": "user", "content": [
                            {"type": "text", "text": "Identifica el material, explica cómo reciclarlo y cuantifica el impacto en CO2 al reciclar, fijate bien el tamaño del producto porque esto es clave para cuantificar el impacto, por lo general son productos de consumo individual, en 100 palabras."},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{imagen}"}}
                        ]}
                    ],
                    max_tokens=1024,
                )
                analisis = respuesta.choices[0].message.content
                st.markdown("**Análisis del producto:**")
                st.write(analisis)

                # Registrar el reciclaje
                registrar_reciclaje(st.session_state.user, analisis)

                audio_content, error = texto_a_voz(analisis)
                if audio_content:
                    with open("temp_audio.mp3", "wb") as f:
                        f.write(audio_content)
                    autoplay_audio("temp_audio.mp3")
                    os.remove("temp_audio.mp3")
                else:
                    st.error(error)

    # Mostrar historial de reciclaje
    st.subheader("Historial de reciclaje")
    historial = obtener_historial_reciclaje(st.session_state.user)
    for descripcion, fecha in historial:
        st.write(f"{fecha}: {descripcion}")

# Manejo de OAuth de Google
def google_login():
    flow = Flow.from_client_config(
        client_config=CLIENT_CONFIG,
        scopes=SCOPES,
        redirect_uri="https://ecogpt.streamlit.app/"
    )
    authorization_url, _ = flow.authorization_url(prompt="consent")
    
    query_params = st.query_params
    if 'code' not in query_params:
        st.markdown(f'<a href="{authorization_url}" class="button">Iniciar sesión con Google</a>', unsafe_allow_html=True)
    else:
        code = query_params['code']
        try:
            flow.fetch_token(code=code)
            credentials = flow.credentials
            user_info_service = build('oauth2', 'v2', credentials=credentials)
            user_info = user_info_service.userinfo().get().execute()
            email = user_info['email']
            google_id = user_info['id']
            st.session_state.user = verificar_usuario_google(google_id, email)
            st.rerun()
        except InvalidGrantError:
            st.error("La sesión ha expirado. Por favor, inicia sesión nuevamente.")
            st.session_state.user = None

# Interfaz principal
if st.session_state.user is None:
    st.title("Bienvenido a EcoGPT")
    st.subheader("Ingresa con tu cuenta de Gmail para utilizar la aplicación.")
    google_login()
else:
    crear_menu_superior()
    main_page()

# Cerrar conexión a la base de datos
conn.close()
