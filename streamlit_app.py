# ==============================================================================
# VERSÃO DE RECUPERAÇÃO - FOCO TOTAL NO LOGIN
# ==============================================================================
import streamlit as st
import os
import pyrebase
import base64
import firebase_admin
from PIL import Image
from firebase_admin import credentials, firestore as firebase_admin_firestore

# --- CONFIGURAÇÃO DE CAMINHOS ---
ASSETS_DIR = "assets"

def get_asset_path(asset_name):
    """Constrói o caminho para um asset dentro da pasta 'assets'."""
    try:
        # O PWD (Print Working Directory) garante que o caminho é relativo ao local do script.
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), ASSETS_DIR, asset_name)
    except Exception:
        # Fallback para ambientes onde __file__ não está definido
        return os.path.join(ASSETS_DIR, asset_name)

# --- CONFIGURAÇÃO DA PÁGINA ---
try:
    page_icon_path = get_asset_path("carinha-agente-max-ia.png")
    page_icon_obj = Image.open(page_icon_path) if os.path.exists(page_icon_path) else "🤖"
except Exception:
    page_icon_obj = "🤖"
st.set_page_config(page_title="Max IA - Acesso", page_icon=page_icon_obj, layout="wide", initial_sidebar_state="collapsed")


# --- CONSTANTES ---
APP_KEY_SUFFIX = "maxia_app_v13.0_login_reset"
USER_COLLECTION = "users"
SALES_PAGE_URL = "https://sua-pagina-de-vendas.com.br"

# --- FUNÇÕES AUXILIARES ---
def convert_image_to_base64(image_name):
    image_path = get_asset_path(image_name)
    try:
        if os.path.exists(image_path):
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode()
    except Exception:
        return None

# --- INICIALIZAÇÃO DE SERVIÇOS ---
@st.cache_resource
def initialize_firebase_services():
    try:
        conf = st.secrets["firebase_config"]
        sa_creds = st.secrets["gcp_service_account"]
        pb_auth = pyrebase.initialize_app(dict(conf)).auth()
        if not firebase_admin._apps:
            cred = credentials.Certificate(dict(sa_creds))
            firebase_admin.initialize_app(cred)
        firestore_db = firebase_admin_firestore.client()
        return pb_auth, firestore_db
    except Exception as e:
        st.error(f"Erro crítico na inicialização do Firebase: {e}")
        return None, None

pb_auth_client, firestore_db = initialize_firebase_services()

def get_current_user_status(auth_client):
    user_auth, uid, email = False, None, None
    session_key = f'{APP_KEY_SUFFIX}_user_session_data'
    if session_key in st.session_state and st.session_state[session_key]:
        try:
            account_info = auth_client.get_account_info(st.session_state[session_key]['idToken'])
            user_auth = True
            uid = account_info['users'][0]['localId']
            email = account_info['users'][0].get('email')
        except Exception:
            st.session_state.clear()
            user_auth = False
    return user_auth, uid, email

# --- INTERFACE DE ENTRADA ---
def exibir_pagina_de_entrada():
    background_image_url = "https://images.pexels.com/photos/3184418/pexels-photo-3184418.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=1"
    logo_base64 = convert_image_to_base64('max-ia-lgo.fundo.transparente.png')
    st.markdown(f"""
        <style>
        .stApp {{ background-image: linear-gradient(rgba(0,0,0,0.6), rgba(0,0,0,0.6)), url("{background_image_url}"); background-size: cover; background-position: center; }}
        .stApp > header, .stSidebar {{ background-color: transparent !important; }}
        .main-container {{ display: flex; flex-direction: column; justify-content: flex-end; align-items: center; height: 90vh; padding-bottom: 5vh; }}
        .logo-container {{ position: absolute; top: 2rem; left: 2rem; }}
        [data-testid="stSidebar"] {{ display: none; }}
        </style>""", unsafe_allow_html=True)

    if logo_base64:
        st.markdown(f"<div class='logo-container'><img src='data:image/png;base64,{logo_base64}' width='150'></div>", unsafe_allow_html=True)
    with st.container():
        st.markdown("<div class='main-container'>", unsafe_allow_html=True)
        _ , col, _ = st.columns([1, 2.5, 1])
        with col:
            if st.button("Já sou cliente", use_container_width=True):
                st.session_state['show_login_form'] = True
                st.rerun()
            if st.button("Ainda não sou cliente", type="secondary", use_container_width=True):
                st.html(f"<script>window.open('{SALES_PAGE_URL}', '_blank')</script>")
        st.markdown("</div>", unsafe_allow_html=True)

def exibir_formularios_de_acesso():
    st.markdown("""<style>[data-testid="stSidebar"] { display: none; }</style>""", unsafe_allow_html=True)
    _ , col, _ = st.columns([1, 1.5, 1])
    with col:
        logo_path = get_asset_path('max-ia-lgo.fundo.transparente.png')
        if os.path.exists(logo_path):
            st.image(logo_path, width=150)
        
        st.header("Acesse sua Central de Comando")
        tab_login, tab_register = st.tabs(["Login", "Registrar"])
        with tab_login:
            with st.form("login_form_main"):
                email = st.text_input("Email", key="login_email")
                password = st.text_input("Senha", type="password", key="login_pass")
                if st.form_submit_button("Entrar", use_container_width=True):
                    try:
                        user_creds = pb_auth_client.sign_in_with_email_and_password(email, password)
                        st.session_state[f'{APP_KEY_SUFFIX}_user_session_data'] = user_creds
                        st.session_state['show_login_form'] = False
                        st.rerun()
                    except Exception:
                        st.error("Email ou senha inválidos.")
        with tab_register:
            with st.form("register_form_main"):
                reg_email = st.text_input("Seu melhor e-mail", key="reg_email")
                reg_password = st.text_input("Crie uma senha forte", type="password", key="reg_pass")
                if st.form_submit_button("Registrar Conta", use_container_width=True):
                    if reg_email and len(reg_password) >= 6:
                        try:
                            new_user = pb_auth_client.create_user_with_email_and_password(reg_email, reg_password)
                            user_data = { "email": reg_email, "registration_date": firebase_admin_firestore.SERVER_TIMESTAMP, "access_level": 2 }
                            firestore_db.collection(USER_COLLECTION).document(new_user['localId']).set(user_data)
                            st.success("Conta criada! Volte para a aba 'Login' para entrar.")
                        except Exception:
                            st.error("Este e-mail já está em uso ou ocorreu um erro.")
                    else:
                        st.warning("Preencha todos os campos corretamente.")

# ==============================================================================
# ESTRUTURA PRINCIPAL E EXECUÇÃO DO APP
# ==============================================================================
def main():
    if not all([pb_auth_client, firestore_db]):
        st.error("Falha crítica na inicialização dos serviços."); st.stop()

    user_is_authenticated, user_uid, user_email = get_current_user_status(pb_auth_client)

    if user_is_authenticated:
        # --- USUÁRIO LOGADO: APENAS UMA MENSAGEM SIMPLES ---
        st.title(f"✅ Login com Sucesso!")
        st.header(f"Bem-vindo, {user_email}")
        st.success("O sistema de autenticação está funcionando corretamente.")
        st.info("Agora que confirmamos o acesso, podemos reintroduzir as outras funcionalidades.")
        
        if st.button("Logout"):
            st.session_state.clear()
            st.rerun()
    else:
        # --- USUÁRIO NÃO LOGADO: MOSTRA LOGIN OU CAPA ---
        if st.session_state.get('show_login_form', False):
            exibir_formularios_de_acesso()
        else:
            exibir_pagina_de_entrada()

if __name__ == "__main__":
    main()
