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

# Tenta carregar o ícone da página, com fallback
try:
    page_icon_path = get_image_path("carinha-agente-max-ia.png")
    page_icon_obj = Image.open(page_icon_path) if os.path.exists(page_icon_path) else "🤖"
except Exception:
    page_icon_obj = "🤖"
st.set_page_config(page_title="Max IA Empresarial", page_icon=page_icon_obj, layout="wide", initial_sidebar_state="collapsed")

# ==============================================================================
# 2. CONSTANTES E CARREGAMENTO DE CONFIGURAÇÕES
# ==============================================================================
APP_KEY_SUFFIX = "maxia_app_v9.2_login_flow"
USER_COLLECTION = "users"
COMPANY_COLLECTION = "companies"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
PROMPTS_CONFIG = carregar_prompts_config()
SALES_PAGE_URL = "https://sua-pagina-de-vendas.com.br" # <-- IMPORTANTE: Substitua por sua URL real

# ==============================================================================
# 3. FUNÇÕES AUXILIARES GLOBAIS
# ==============================================================================
def convert_image_to_base64(image_name):
    # Esta função agora é mais robusta para lidar com caminhos
    image_path = get_image_path(image_name)
    try:
        if os.path.exists(image_path):
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode()
    except Exception as e:
        print(f"ERRO convert_image_to_base64: {e}")
    return None

def gerar_arquivo_download(conteudo, formato):
    if formato == "txt":
        return io.BytesIO(conteudo.encode("utf-8"))
    elif formato == "docx":
        document = Document()
        document.add_paragraph(conteudo)
        bio = io.BytesIO()
        document.save(bio)
        bio.seek(0)
        return bio
    elif formato == "pdf":
        pdf = FPDF()
        pdf.add_page()
        caminho_fonte = get_font_path("DejaVuSans.ttf")
        try:
            pdf.add_font('DejaVu', '', caminho_fonte, uni=True)
            pdf.set_font('DejaVu', '', 12)
        except RuntimeError:
            print(f"AVISO: Fonte '{caminho_fonte}' não encontrada.")
            pdf.set_font("Arial", size=12)
        
        # Codifica corretamente para o FPDF
        conteudo_formatado = conteudo.encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 10, txt=conteudo_formatado)
        return io.BytesIO(pdf.output(dest='S').encode('latin-1'))
    return None

# ==============================================================================
# 4. INICIALIZAÇÃO DE SERVIÇOS E AUTENTICAÇÃO
# ==============================================================================
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

@st.cache_resource
def get_llm():
    try:
        api_key = st.secrets.get("GOOGLE_API_KEY")
        if api_key:
            return ChatGoogleGenerativeAI(model="gemini-1.5-pro-latest", google_api_key=api_key, temperature=0.75)
        else:
            st.error("Chave GOOGLE_API_KEY não configurada.")
            return None
    except Exception as e:
        st.error(f"Erro ao inicializar LLM: {e}")
        return None

def get_current_user_status(auth_client):
    user_auth, uid, email = False, None, None
    session_key = f'{APP_KEY_SUFFIX}_user_session_data'
    if session_key in st.session_state and st.session_state[session_key]:
        try:
            # Tenta validar o token
            account_info = auth_client.get_account_info(st.session_state[session_key]['idToken'])
            user_auth = True
            user_info = account_info['users'][0]
            uid = user_info['localId']
            email = user_info.get('email')
            st.session_state.update({'user_is_authenticated': True, 'user_uid': uid, 'user_email': email})
        except Exception:
            # Se o token expirar ou for inválido, limpa a sessão
            st.session_state.clear()
            user_auth = False
    return user_auth, uid, email

# ==============================================================================
# 5. CLASSE PRINCIPAL DO AGENTE (com placeholders)
# ==============================================================================
class MaxAgente:
    def __init__(self, llm_instance, db_firestore_instance):
        self.llm = llm_instance
        self.db = db_firestore_instance

    # Funções de onboarding e painéis principais (placeholders)
    def exibir_onboarding_calibracao(self): st.title("Calibração da Empresa...")
    def exibir_onboarding_trainer(self): st.title("Personalização da Experiência...")
    def exibir_tour_guiado(self): st.title("Tour Guiado...")
    def exibir_painel_boas_vindas(self): 
        st.title("👋 Bem-vindo ao seu Centro de Comando!")
        st.markdown("Use o menu à esquerda para navegar entre os Agentes Max IA.")
    def exibir_max_marketing_total(self): st.header("🚀 MaxMarketing Total")
    def exibir_max_trainer_ia(self): st.header("🎓 MaxTrainer IA")
    def exibir_central_cliente(self): st.header("📈 Central do Cliente 360°")
    def exibir_max_administrativo(self): st.header("⚙️ MaxAdministrativo")
    def exibir_max_financeiro(self): st.header("💰 MaxFinanceiro")
    def exibir_max_construtor(self): st.header("🏗️ MaxConstrutor")

# ==============================================================================
# 6. NOVAS FUNÇÕES DA INTERFACE DE ENTRADA
# ==============================================================================
def exibir_pagina_de_entrada():
    """Renderiza a capa de abertura inspirada no modelo visual."""

    # Estilo para sobrepor o conteúdo na imagem de fundo
    background_image_url = "https://images.pexels.com/photos/3184418/pexels-photo-3184418.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=1"
    logo_base64 = convert_image_to_base64('max-ia-lgo.fundo.transparente.png')

    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: linear-gradient(rgba(0,0,0,0.5), rgba(0,0,0,0.5)), url("{background_image_url}");
            background-size: cover;
            background-position: center;
        }}
        .stApp > header {{
            background-color: transparent;
        }}
        .stButton button {{
            width: 100%;
            height: 3rem;
            font-size: 1.1rem;
            font-weight: 600;
        }}
        .main-container {{
            display: flex;
            flex-direction: column;
            justify-content: flex-end;
            align-items: center;
            height: 85vh;
            padding-bottom: 5vh;
        }}
        .logo-container {{
            position: absolute;
            top: 2rem;
            left: 2rem;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

    if logo_base64:
        st.markdown(f"<div class='logo-container'><img src='data:image/png;base64,{logo_base64}' width='150'></div>", unsafe_allow_html=True)

    with st.container():
        st.markdown("<div class='main-container'>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("Já sou cliente"):
                st.session_state['show_login_form'] = True
                st.rerun()

            if st.button("Ainda não sou cliente"):
                js = f"window.open('{SALES_PAGE_URL}', '_blank')"
                st.html(f"<script>{js}</script>")

            st.caption("Ao continuar, você aceita nossos [Termos e condições](https://seus-termos.com.br).")
        st.markdown("</div>", unsafe_allow_html=True)

def exibir_formularios_de_acesso():
    """Renderiza os formulários de login e registro no corpo da página."""
    st.title("Acesse sua Central de Comando")
    
    tab_login, tab_register = st.tabs(["Login", "Registrar"])

    with tab_login:
        with st.form("login_form_main"):
            email = st.text_input("Email")
            password = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar"):
                try:
                    user_creds = pb_auth_client.sign_in_with_email_and_password(email, password)
                    st.session_state[f'{APP_KEY_SUFFIX}_user_session_data'] = user_creds
                    st.session_state['show_login_form'] = False # Limpa o estado
                    st.rerun()
                except Exception:
                    st.error("Email ou senha inválidos.")
    
    with tab_register:
        with st.form("register_form_main"):
            email = st.text_input("Seu Email")
            password = st.text_input("Crie uma Senha (mínimo 6 caracteres)", type="password")
            if st.form_submit_button("Registrar Conta"):
                if email and len(password) >= 6:
                    try:
                        new_user = pb_auth_client.create_user_with_email_and_password(email, password)
                        # Prepara o documento do novo usuário no Firestore
                        user_data = {
                            "email": email,
                            "registration_date": firebase_admin_firestore.SERVER_TIMESTAMP,
                            "access_level": 2, # Nível padrão para novos registros
                            "analogy_domain": None,
                            "company_id": None
                        }
                        firestore_db.collection(USER_COLLECTION).document(new_user['localId']).set(user_data)
                        st.success("Conta criada com sucesso! Volte para a aba 'Login' para entrar.")
                    except Exception as e:
                        st.error("Este e-mail já está em uso ou ocorreu um erro.")
                else:
                    st.warning("Por favor, preencha todos os campos corretamente.")

# ==============================================================================
# 7. ESTRUTURA PRINCIPAL E EXECUÇÃO DO APP (FLUXO ATUALIZADO)
# ==============================================================================
def main():
    if not all([pb_auth_client, firestore_db, PROMPTS_CONFIG]):
        st.error("Falha crítica na inicialização dos serviços. O aplicativo não pode continuar.")
        st.stop()

    user_is_authenticated, user_uid, user_email = get_current_user_status(pb_auth_client)

    if user_is_authenticated:
        # USUÁRIO LOGADO - INICIA A APLICAÇÃO PRINCIPAL
        st.sidebar.image(get_image_path('max-ia-lgo.fundo.transparente.png'), width=100)
        st.sidebar.title("Max IA Empresarial")
        st.sidebar.markdown("---")
        
        if 'agente' not in st.session_state:
            llm = get_llm()
            if llm and firestore_db:
                st.session_state.agente = MaxAgente(llm, firestore_db)
            else:
                st.error("Agente Max IA não pôde ser inicializado.")
                st.stop()
        
        agente = st.session_state.agente
        
        try:
            user_doc_ref = firestore_db.collection(USER_COLLECTION).document(user_uid)
            user_doc = user_doc_ref.get()
            user_data = user_doc.to_dict() if user_doc.exists else None
        except Exception as e:
            st.error(f"Erro ao buscar dados do usuário: {e}")
            st.stop()

        if not user_data:
            # Cria o documento do usuário se ele não existir (caso raro)
            user_data = {"email": user_email, "registration_date": firebase_admin_firestore.SERVER_TIMESTAMP, "access_level": 2, "analogy_domain": None, "company_id": None}
            user_doc_ref.set(user_data)
        
        # --- LÓGICA DE ONBOARDING E TOUR ---
        if user_data.get("company_id"):
            if user_data.get("analogy_domain"):
                if st.session_state.get('start_guided_tour', False):
                    agente.exibir_tour_guiado()
                else:
                    # --- APLICAÇÃO PRINCIPAL ---
                    st.sidebar.write(f"Logado como: **{user_email}**")
                    st.sidebar.caption(f"Nível de Acesso: {user_data.get('access_level', 'N/D')}")
                    if st.sidebar.button("Logout", key=f"{APP_KEY_SUFFIX}_logout"):
                        st.session_state.clear()
                        st.rerun()
                    
                    opcoes_menu = {
                        "👋 Bem-vindo": agente.exibir_painel_boas_vindas,
                        "🚀 MaxMarketing Total": agente.exibir_max_marketing_total,
                        "🎓 MaxTrainer IA": agente.exibir_max_trainer_ia,
                        "📈 Central do Cliente 360°": agente.exibir_central_cliente,
                        "⚙️ MaxAdministrativo": agente.exibir_max_administrativo,
                        "💰 MaxFinanceiro": agente.exibir_max_financeiro,
                        "🏗️ MaxConstrutor": agente.exibir_max_construtor,
                    }
                    
                    # Filtra o menu com base no nível de acesso (exemplo)
                    # if user_data.get('access_level') != 1:
                    #     del opcoes_menu["💰 MaxFinanceiro"]

                    selecao_label = st.sidebar.radio("Max Agentes IA:", list(opcoes_menu.keys()), key=f"{APP_KEY_SUFFIX}_menu")
                    opcoes_menu[selecao_label]()
            else:
                agente.exibir_onboarding_trainer()
        else:
            agente.exibir_onboarding_calibracao()
    else:
        # USUÁRIO NÃO LOGADO - MOSTRA A TELA DE ENTRADA OU LOGIN
        if st.session_state.get('show_login_form', False):
            exibir_formularios_de_acesso()
        else:
            exibir_pagina_de_entrada()

if __name__ == "__main__":
    main()
