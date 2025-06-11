# ==============================================================================
# streamlit_app.py (v9.0 - ARQUITETURA DE EMPRESAS FUNCIONAL)
# ==============================================================================

# 1. IMPORTAÇÕES E CONFIGURAÇÃO INICIAL DA PÁGINA
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
APP_KEY_SUFFIX = "maxia_app_v9.0_empresas"
USER_COLLECTION = "users"
COMPANY_COLLECTION = "companies"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
PROMPTS_CONFIG = carregar_prompts_config()

# 3. FUNÇÕES AUXILIARES GLOBAIS
def convert_image_to_base64(image_name):
    image_path = get_image_path(image_name)
    try:
        if os.path.exists(image_path):
            with open(image_path, "rb") as image_file: return base64.b64encode(image_file.read()).decode()
    except Exception as e: print(f"ERRO convert_image_to_base64: {e}")
    return None

# (outras funções auxiliares como gerar_arquivo_download podem ser mantidas aqui)

# 4. INICIALIZAÇÃO DE SERVIÇOS E AUTENTICAÇÃO
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
    # (código da função get_current_user_status sem alterações)
    user_auth, uid, email = False, None, None; session_key = f'{APP_KEY_SUFFIX}_user_session_data'
    if session_key in st.session_state and st.session_state[session_key]:
        try:
            account_info = auth_client.get_account_info(st.session_state[session_key]['idToken'])
            user_auth = True; user_info = account_info['users'][0]
            uid = user_info['localId']; email = user_info.get('email')
            st.session_state.update({'user_is_authenticated': user_auth, 'user_uid': uid, 'user_email': email})
        except Exception:
            st.session_state.clear(); user_auth = False
    return user_auth, uid, email

# ==============================================================================
# 5. CLASSE PRINCIPAL DO AGENTE
# ==============================================================================
class MaxAgente:
    def __init__(self, llm_instance, db_firestore_instance):
        self.llm = llm_instance
        self.db = db_firestore_instance

    # --- MÉTODOS GERAIS E DE ONBOARDING ---
    def exibir_onboarding_calibracao(self):
        st.title("Vamos calibrar o seu Max IA Empresarial! ⚙️")
        st.markdown("Para que eu possa ser um copiloto realmente eficaz, preciso entender um pouco sobre o seu negócio. Responda a algumas perguntas rápidas para começarmos.")
        with st.form(key="calibration_form"):
            st.subheader("1. Conhecendo a Empresa")
            company_name = st.text_input("Nome da Empresa", placeholder="Ex: Padaria do Zé")
            setor = st.selectbox("Setor de Atuação", ["Varejo", "Serviços", "Indústria", "Saúde", "TI", "Alimentação", "Outro"])
            submitted = st.form_submit_button("Criar Minha Empresa e Continuar")
            if submitted:
                if not company_name:
                    st.warning("O nome da empresa é essencial.")
                else:
                    user_uid = st.session_state.get('user_uid')
                    if user_uid and self.db:
                        with st.spinner("Criando o centro de comando da sua empresa..."):
                            try:
                                company_ref = self.db.collection(COMPANY_COLLECTION).document()
                                company_data = {"company_name": company_name, "owner_uid": user_uid, "setor": setor, "created_at": firebase_admin.firestore.SERVER_TIMESTAMP}
                                company_ref.set(company_data)
                                user_ref = self.db.collection(USER_COLLECTION).document(user_uid)
                                user_ref.update({"company_id": company_ref.id})
                                st.success(f"A empresa '{company_name}' foi criada!")
                                time.sleep(2)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Ocorreu um erro ao criar sua empresa: {e}")

    def exibir_onboarding_trainer(self):
        st.title("Quase lá! Vamos personalizar sua experiência.")
        st.markdown("Para que suas interações com o Max IA sejam perfeitas, me conte sobre um assunto que você gosta. Assim, posso te explicar os conceitos mais complexos de negócios de um jeito que faça sentido para você.")
        opcoes_analogia = ["Futebol", "Culinária", "Carros", "Cinema e Séries", "Música", "Moda", "Negócios (tradicional)"]
        dominio_escolhido = st.selectbox("Escolha um assunto abaixo:", opcoes_analogia, key="analogy_choice")
        if st.button("Salvar e Começar a Usar!", key="save_analogy_domain"):
            user_uid = st.session_state.get('user_uid')
            if user_uid and self.db:
                try:
                    user_ref = self.db.collection(USER_COLLECTION).document(user_uid)
                    user_ref.update({"analogy_domain": dominio_escolhido.lower()})
                    st.session_state['start_guided_tour'] = True
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar sua preferência: {e}")

    def exibir_tour_guiado(self):
        st.balloons()
        st.title("🎉 Bem-vindo ao seu Centro de Comando!")
        st.markdown("Eu sou o Max, seu copiloto de IA. Minha missão é te ajudar a tomar as melhores decisões.")
        st.info("Passei os últimos segundos analisando os dados da sua 'calibração' e preparei a plataforma para você. Note que o menu à esquerda já está disponível.")
        if st.button("Entendido, vamos começar!"):
            st.session_state['start_guided_tour'] = False
            st.rerun()

    def exibir_painel_boas_vindas(self):
        st.markdown("<div style='text-align: center;'><h1>👋 Bem-vindo ao Max IA!</h1></div>", unsafe_allow_html=True)
        # (código do logo...)

    ## --- SUB-MÓDULO 5.1: MaxMarketing Total --- ##
    def exibir_max_marketing_total(self):
        st.info("Agente MaxMarketing em desenvolvimento.")

    ## --- SUB-MÓDULO 5.5: MaxTrainer IA --- ##
    def exibir_max_trainer_ia(self):
        st.title("🎓 MaxTrainer IA")
        # (código completo do chat aqui...)

# ==============================================================================
# 6. ESTRUTURA PRINCIPAL E EXECUÇÃO DO APP
# ==============================================================================
def main():
    if not all([pb_auth_client, firestore_db, PROMPTS_CONFIG]):
        st.error("Falha crítica na inicialização dos serviços."); st.stop()

    user_is_authenticated, user_uid, user_email = get_current_user_status(pb_auth_client)

    if user_is_authenticated:
        if 'agente' not in st.session_state:
            llm = get_llm()
            if llm and firestore_db:
                st.session_state.agente = MaxAgente(llm, firestore_db)
        
        agente = st.session_state.get('agente')
        if agente:
            try:
                user_doc_ref = firestore_db.collection(USER_COLLECTION).document(user_uid)
                user_doc = user_doc_ref.get()
                user_data = user_doc.to_dict() if user_doc.exists else None
            except Exception as e:
                st.error(f"Erro ao buscar dados do usuário: {e}"); user_data = None; st.stop()

            if not user_data:
                # Cria o documento do usuário se ele não existir
                user_data = {"email": user_email, "registration_date": firebase_admin.firestore.SERVER_TIMESTAMP, "analogy_domain": None, "company_id": None}
                user_doc_ref.set(user_data)
            
            # --- LÓGICA DE ONBOARDING E TOUR ---
            if user_data.get("company_id"):
                if user_data.get("analogy_domain"):
                    if st.session_state.get('start_guided_tour', False):
                        agente.exibir_tour_guiado()
                    else:
                        # --- APLICAÇÃO PRINCIPAL ---
                        st.sidebar.title("Max IA")
                        st.sidebar.markdown(f"**Empresa:** *Buscando...*") # Placeholder
                        st.sidebar.markdown("---")
                        st.sidebar.write(f"Logado como: **{user_email}**")
                        if st.sidebar.button("Logout", key=f"{APP_KEY_SUFFIX}_logout"):
                            st.session_state.clear(); st.rerun()
                        
                        opcoes_menu = {
                            "👋 Bem-vindo": agente.exibir_painel_boas_vindas,
                            "🚀 MaxMarketing Total": agente.exibir_max_marketing_total,
                            "🎓 MaxTrainer IA": agente.exibir_max_trainer_ia,
                        }
                        selecao_label = st.sidebar.radio("Max Agentes IA:", list(opcoes_menu.keys()))
                        opcoes_menu[selecao_label]()
                else:
                    agente.exibir_onboarding_trainer()
            else:
                agente.exibir_onboarding_calibracao()
        else:
            st.error("Agente Max IA não pôde ser carregado.")
    else:
        # --- BLOCO DE LOGIN E REGISTRO ---
        st.title("🔑 Bem-vindo ao Max IA")
        auth_action = st.sidebar.radio("Acesso:", ["Login", "Registrar"])
        if auth_action == "Login":
            with st.sidebar.form("login_form"):
                email = st.text_input("Email")
                password = st.text_input("Senha", type="password")
                if st.form_submit_button("Entrar"):
                    try:
                        user_creds = pb_auth_client.sign_in_with_email_and_password(email, password)
                        st.session_state[f'{APP_KEY_SUFFIX}_user_session_data'] = user_creds
                        st.rerun()
                    except Exception:
                        st.sidebar.error("Erro no login.")
        else: 
            with st.sidebar.form("register_form"):
                email = st.text_input("Email")
                password = st.text_input("Crie uma Senha", type="password")
                if st.form_submit_button("Registrar Conta"):
                    try:
                        new_user = pb_auth_client.create_user_with_email_and_password(email, password)
                        user_data = {"email": email, "registration_date": firebase_admin.firestore.SERVER_TIMESTAMP, "analogy_domain": None, "company_id": None}
                        firestore_db.collection(USER_COLLECTION).document(new_user['localId']).set(user_data)
                        st.sidebar.success("Conta criada! Faça o login.")
                    except Exception as e:
                        st.sidebar.error("E-mail já em uso ou erro no registro.")
# ... (final do bloco de Registro de nova conta) ...
                    else:
                        st.sidebar.warning("Preencha todos os campos corretamente.")
    
    # >>>>> ADICIONE AS DUAS LINHAS AQUI <<<<<
    st.sidebar.markdown("---")
    st.sidebar.info("Max IA | by Yaakov Israel & Gemini AI")

if __name__ == "__main__":
    main()
    
if __name__ == "__main__":
    main()
