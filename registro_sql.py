import streamlit as st
import sqlite3
import bcrypt
import re

# Configuración inicial de la página
st.set_page_config(page_title="Login App", layout="centered")

# Conexión a la base de datos
conn = sqlite3.connect('users.db')
c = conn.cursor()

# Crear tabla de usuarios si no existe
c.execute('''CREATE TABLE IF NOT EXISTS users
             (email TEXT PRIMARY KEY, password TEXT)''')
conn.commit()

# Función para validar el formato del correo electrónico
def is_valid_email(email):
    pattern = r'^[\w\.-]+@gmail\.com$'
    return re.match(pattern, email) is not None

# Función para registrar un nuevo usuario
def register_user(email, password):
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    try:
        c.execute("INSERT INTO users (email, password) VALUES (?, ?)", (email, hashed))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

# Función para verificar las credenciales del usuario
def verify_user(email, password):
    c.execute("SELECT password FROM users WHERE email = ?", (email,))
    result = c.fetchone()
    if result:
        return bcrypt.checkpw(password.encode('utf-8'), result[0])
    return False

# Función para la página principal
def main_page():
    st.title("Bienvenido a la Aplicación")
    st.write(f"Has iniciado sesión como: {st.session_state.user}")
    # Aquí puedes agregar el contenido de tu aplicación principal

# Inicialización de la sesión
if 'user' not in st.session_state:
    st.session_state.user = None

# Interfaz de usuario
if st.session_state.user is None:
    choice = st.selectbox("Login/Signup", ['Login', 'Sign Up'])
    
    if choice == 'Sign Up':
        st.subheader("Crear Nueva Cuenta")
        new_user = st.text_input("Email (Gmail)")
        new_password = st.text_input("Contraseña", type='password')
        
        if st.button("Signup"):
            if is_valid_email(new_user):
                if register_user(new_user, new_password):
                    st.success("Cuenta creada exitosamente!")
                    st.info("Por favor inicia sesión con tus nuevas credenciales")
                else:
                    st.error("El email ya está registrado")
            else:
                st.error("Por favor, usa una dirección de Gmail válida")
                
    else:
        st.subheader("Iniciar Sesión")
        user = st.text_input("Email")
        password = st.text_input("Contraseña", type='password')
        
        if st.button("Login"):
            if verify_user(user, password):
                st.session_state.user = user
                st.experimental_rerun()
            else:
                st.error("Email o contraseña incorrectos")
else:
    main_page()
    if st.button("Logout"):
        st.session_state.user = None
        st.experimental_rerun()

# Cerrar la conexión a la base de datos cuando la aplicación se cierre
conn.close()