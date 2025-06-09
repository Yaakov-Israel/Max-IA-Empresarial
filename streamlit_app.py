# ==============================================================================
# streamlit_app.py (v7.1 - FOCO TOTAL EM VITRINE DIGITAL)
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
APP_KEY_SUFFIX = "maxia_app_v7.1_vitrine_focus"
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

# 5. CLASSE PRINCIPAL DO AGENTE
# ==============================================================================
class MaxAgente:
    def __init__(self, llm_instance, db_firestore_instance):
        self.llm = llm_instance
        self.db = db_firestore_instance

    def exibir_painel_boas_vindas(self):
        st.markdown("<div style='text-align: center;'><h1>👋 Bem-vindo ao Max IA!</h1></div>", unsafe_allow_html=True)
        logo_base64 = convert_image_to_base64('max-ia-logo.png')
        if logo_base64:
            st.markdown(f"<div style='text-align: center;'><img src='data:image/png;base64,{logo_base64}' width='200'></div>", unsafe_allow_html=True)
        st.markdown("<div style='text-align: center;'><p style='font-size: 1.2em;'>Olá! Eu sou o <strong>Max</strong>, seu assistente de IA para impulsionar o sucesso da sua empresa.</p></div>", unsafe_allow_html=True)

    def exibir_max_marketing_total(self):
        st.header("🚀 MaxMarketing Total")
        st.caption("Seu copiloto para criar posts, campanhas e muito mais!")
        st.info("Em desenvolvimento...")

    def exibir_max_construtor(self):
        st.header("🏗️ Max Vitrine Digital")
        st.caption("Crie uma página de vendas para seus produtos ou serviços.")
        st.markdown("---")

        # A lógica da entrevista, geração e ateliê virá aqui.
        # Por enquanto, é um placeholder funcional.
        st.info("Em construção: A entrevista inteligente para criar sua Vitrine Digital.")


    def exibir_max_financeiro(self): st.header("💰 MaxFinanceiro"); st.info("Em breve...")
    def exibir_max_administrativo(self): st.header("⚙️ MaxAdministrativo"); st.info("Em breve...")
    def exibir_max_pesquisa_mercado(self): st.header("📈 MaxPesquisa de Mercado"); st.info("Em breve...")
    def exibir_max_bussola(self): st.header("🧭 MaxBússola Estratégica"); st.info("Em breve...")
    def exibir_max_trainer(self): st.header("🎓 MaxTrainer IA"); st.info("Em breve...")

# 6. ESTRUTURA PRINCIPAL E EXECUÇÃO DO APP
# ==============================================================================
def main():
    if not all([pb_auth_client, firestore_db, PROMPTS_CONFIG]):
        st.stop()

    user_is_authenticated, _, user_email = get_current_user_status(pb_auth_client)

    if user_is_authenticated:
        llm = get_llm()
        if 'agente' not in st.session_state and llm:
            st.session_state.agente = MaxAgente(llm, firestore_db)
        
        if 'agente' in st.session_state:
            agente = st.session_state.agente
            st.sidebar.title("Max IA")
            st.sidebar.markdown("---")
            st.sidebar.write(f"Logado como: **{user_email}**")

            if st.sidebar.button("Logout", key=f"{APP_KEY_SUFFIX}_logout"):
                for k in list(st.session_state.keys()):
                    del st.session_state[k]
                st.rerun()

            opcoes_menu = {
                "👋 Bem-vindo": agente.exibir_painel_boas_vindas,
                "🚀 Marketing": agente.exibir_max_marketing_total,
                "🏗️ Max Construtor": agente.exibir_max_construtor,
                "💰 Financeiro": agente.exibir_max_financeiro,
                "⚙️ Administrativo": agente.exibir_max_administrativo,
                "📈 Pesquisa": agente.exibir_max_pesquisa_mercado,
                "🧭 Estratégia": agente.exibir_max_bussola,
                "🎓 Trainer": agente.exibir_max_trainer
            }
            
            selecao_label = st.sidebar.radio("Max Agentes IA:", list(opcoes_menu.keys()), key=f"main_nav_{APP_KEY_SUFFIX}")
            opcoes_menu[selecao_label]()
        else:
            st.error("Agente Max IA não carregado.")
    else:
        st.title("🔑 Bem-vindo ao Max IA")
        st.info("Faça login ou registre-se na barra lateral.")
        logo_base64 = convert_image_to_base64('max-ia-logo.png')
        if logo_base64:
            st.image(f"data:image/png;base64,{logo_base64}", width=200)

        auth_action = st.sidebar.radio("Acesso:", ["Login", "Registrar"], key=f"{APP_KEY_SUFFIX}_auth_choice")
        if auth_action == "Login":
            with st.sidebar.form(f"{APP_KEY_SUFFIX}_login_form"):
                email = st.text_input("Email")
                password = st.text_input("Senha", type="password")
                if st.form_submit_button("Entrar"):
                    try:
                        st.session_state[f'{APP_KEY_SUFFIX}_user_session_data'] = dict(pb_auth_client.sign_in_with_email_and_password(email, password))
                        st.rerun()
                    except Exception:
                        st.sidebar.error("Login falhou.")
        else:
            with st.sidebar.form(f"{APP_KEY_SUFFIX}_register_form"):
                email = st.text_input("Seu Email")
                password = st.text_input("Crie uma Senha", type="password")
                if st.form_submit_button("Registrar"):
                    if email and len(password) >= 6:
                        try:
                            new_user = pb_auth_client.create_user_with_email_and_password(email, password)
                            firestore_db.collection(USER_COLLECTION).document(new_user['localId']).set({"email": email, "registration_date": firebase_admin.firestore.SERVER_TIMESTAMP}, merge=True)
                            st.sidebar.success("Conta criada! Faça o login.")
                        except Exception:
                            st.sidebar.error("E-mail já em uso ou erro no registro.")
                    else:
                        st.sidebar.warning("Dados inválidos.")
    
    st.sidebar.markdown("---")
    st.sidebar.info("Max IA | by Yaakov Israel & Gemini AI")

if __name__ == "__main__":
    main()
