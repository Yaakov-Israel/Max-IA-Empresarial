# ==============================================================================
# streamlit_app.py (v8.0 - DOUTRINA DA CONSTRUÇÃO MODULAR)
# ==============================================================================

# 1. IMPORTAÇÕES E CONFIGURAÇÃO INICIAL DA PÁGINA
# ==============================================================================
import streamlit as st
import os
import io
import json
import pyrebase
import base64
import time
import datetime
import firebase_admin
from PIL import Image
from docx import Document
from fpdf import FPDF
from langchain_google_genai import ChatGoogleGenerativeAI
from firebase_admin import credentials, firestore as firebase_admin_firestore
from utils import carregar_prompts_config, get_image_path, get_font_path

try:
    page_icon_path = get_image_path("carinha-agente-max-ia.png")
    page_icon_obj = Image.open(page_icon_path) if os.path.exists(page_icon_path) else "🤖"
except Exception:
    page_icon_obj = "🤖"
st.set_page_config(page_title="Max IA", page_icon=page_icon_obj, layout="wide", initial_sidebar_state="expanded")

# 2. CONSTANTES E CARREGAMENTO DE CONFIGURAÇÕES
# ==============================================================================
APP_KEY_SUFFIX = "maxia_app_v8.0_modular"
USER_COLLECTION = "users"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
PROMPTS_CONFIG = carregar_prompts_config()

# 3. FUNÇÕES AUXILIARES GLOBAIS
# ==============================================================================
def convert_image_to_base64(image_name):
    image_path = get_image_path(image_name)
    try:
        if os.path.exists(image_path):
            with open(image_path, "rb") as image_file: return base64.b64encode(image_file.read()).decode()
    except Exception as e: print(f"ERRO convert_image_to_base64: {e}")
    return None

def gerar_arquivo_download(conteudo, formato):
    if formato == "txt": return io.BytesIO(conteudo.encode("utf-8"))
    elif formato == "docx":
        document = Document(); document.add_paragraph(conteudo); bio = io.BytesIO(); document.save(bio); bio.seek(0)
        return bio
    elif formato == "pdf":
        pdf = FPDF(); pdf.add_page(); caminho_fonte = get_font_path("DejaVuSans.ttf")
        try:
            pdf.add_font('DejaVu', '', caminho_fonte, uni=True); pdf.set_font('DejaVu', '', 12)
        except RuntimeError:
            print(f"AVISO: Fonte '{caminho_fonte}' não encontrada."); pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 10, txt=conteudo.encode('latin-1', 'replace').decode('latin-1'))
        return io.BytesIO(pdf.output(dest='S'))
    return None

# 4. INICIALIZAÇÃO DE SERVIÇOS E AUTENTICAÇÃO
# ==============================================================================
@st.cache_resource
def initialize_firebase_services():
    try:
        conf = st.secrets["firebase_config"]; sa_creds = st.secrets["gcp_service_account"]
        pb_auth = pyrebase.initialize_app(dict(conf)).auth()
        if not firebase_admin._apps:
            cred = credentials.Certificate(dict(sa_creds)); firebase_admin.initialize_app(cred)
        firestore_db = firebase_admin_firestore.client()
        return pb_auth, firestore_db
    except Exception as e: st.error(f"Erro crítico na inicialização do Firebase: {e}"); return None, None

pb_auth_client, firestore_db = initialize_firebase_services()

@st.cache_resource
def get_llm():
    try:
        api_key = st.secrets.get("GOOGLE_API_KEY")
        if api_key: return ChatGoogleGenerativeAI(model="gemini-1.5-pro-latest", google_api_key=api_key, temperature=0.75)
        else: st.error("Chave GOOGLE_API_KEY não configurada."); return None
    except Exception as e: st.error(f"Erro ao inicializar LLM: {e}"); return None

def get_current_user_status(auth_client):
    user_auth, uid, email = False, None, None; session_key = f'{APP_KEY_SUFFIX}_user_session_data'
    if session_key in st.session_state and st.session_state[session_key]:
        try:
            account_info = auth_client.get_account_info(st.session_state[session_key]['idToken'])
            user_auth = True; user_info = account_info['users'][0]
            uid = user_info['localId']; email = user_info.get('email')
            st.session_state[session_key].update({'localId': uid, 'email': email})
        except Exception:
            st.session_state.pop(session_key, None); user_auth = False
            if 'auth_error_shown' not in st.session_state:
                st.sidebar.warning("Sessão inválida."); st.session_state['auth_error_shown'] = True
            st.rerun()
    st.session_state.user_is_authenticated = user_auth; st.session_state.user_uid = uid; st.session_state.user_email = email
    return user_auth, uid, email
