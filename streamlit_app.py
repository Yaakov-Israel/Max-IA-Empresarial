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
import pandas as pd
from PIL import Image
from docx import Document
from fpdf import FPDF
from langchain_google_genai import ChatGoogleGenerativeAI
from firebase_admin import credentials, firestore as firebase_admin_firestore

# --- INÍCIO DA CONFIGURAÇÃO DE CAMINHOS E DIRETÓRIOS ---
# Padroniza o diretório de assets para robustez na implantação.
# CRIE UMA PASTA CHAMADA "assets" NA RAIZ DO SEU PROJETO E COLOQUE SUAS IMAGENS E FONTES LÁ.
ASSETS_DIR = "assets"

def get_asset_path(asset_name):
    """Constrói o caminho para um asset dentro da pasta 'assets'."""
    # O PWD (Print Working Directory) garante que o caminho é relativo ao local do script.
    return os.path.join(os.path.dirname(__file__), ASSETS_DIR, asset_name)

# Tenta carregar o ícone da página, com fallback
try:
    page_icon_path = get_asset_path("carinha-agente-max-ia.png")
    page_icon_obj = Image.open(page_icon_path) if os.path.exists(page_icon_path) else "🤖"
except Exception:
    page_icon_obj = "🤖"
st.set_page_config(page_title="Max IA Empresarial", page_icon=page_icon_obj, layout="wide", initial_sidebar_state="collapsed")
# --- FIM DA CONFIGURAÇÃO DE CAMINHOS ---

# ==============================================================================
# 2. CONSTANTES E CARREGAMENTO DE CONFIGURAÇÕES
# ==============================================================================
APP_KEY_SUFFIX = "maxia_app_v10.1_integrated_fixed"
USER_COLLECTION = "users"
COMPANY_COLLECTION = "companies"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
SALES_PAGE_URL = "https://sua-pagina-de-vendas.com.br" # <-- IMPORTANTE: Substitua por sua URL real

@st.cache_data
def carregar_prompts_config():
    return {"versao": "1.0"}

PROMPTS_CONFIG = carregar_prompts_config()

# ==============================================================================
# 3. FUNÇÕES AUXILIARES GLOBAIS
# ==============================================================================
def convert_image_to_base64(image_name):
    image_path = get_asset_path(image_name)
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
        caminho_fonte = get_asset_path("DejaVuSans.ttf")
        try:
            pdf.add_font('DejaVu', '', caminho_fonte, uni=True)
            pdf.set_font('DejaVu', '', 12)
        except RuntimeError:
            print(f"AVISO: Fonte '{caminho_fonte}' não encontrada. Usando Arial.")
            pdf.set_font("Arial", size=12)
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
            account_info = auth_client.get_account_info(st.session_state[session_key]['idToken'])
            user_auth = True
            user_info = account_info['users'][0]
            uid = user_info['localId']
            email = user_info.get('email')
            st.session_state.update({'user_is_authenticated': True, 'user_uid': uid, 'user_email': email})
        except Exception:
            st.session_state.clear()
            user_auth = False
    return user_auth, uid, email

# ==============================================================================
# 5. CLASSE PRINCIPAL DO AGENTE (FUNCIONALIDADES INTEGRADAS)
# ==============================================================================
class MaxAgente:
    def __init__(self, llm_instance, db_firestore_instance):
        self.llm = llm_instance
        self.db = db_firestore_instance

    def exibir_painel_boas_vindas(self):
        st.title("👋 Bem-vindo ao seu Centro de Comando!")
        st.markdown("Use o menu à esquerda para navegar entre os Agentes Max IA e transformar a gestão da sua empresa.")
        logo_path = get_asset_path('max-ia-lgo.fundo.transparente.png')
        if os.path.exists(logo_path):
            st.image(logo_path, width=200)

    # --- 5.1: MaxFinanceiro ---
    def exibir_max_financeiro(self):
        st.header("💰 MaxFinanceiro")
        st.caption("O Cérebro Financeiro da sua empresa em Tempo Real.")

        vendas_dia, contas_receber, saldo_caixa = 1250.75, 7500.50, 12345.67
        col1, col2, col3 = st.columns(3)
        col1.metric("Vendas do Dia", f"R$ {vendas_dia:,.2f}", "150.25")
        col2.metric("Contas a Receber", f"R$ {contas_receber:,.2f}")
        col3.metric("Saldo em Caixa", f"R$ {saldo_caixa:,.2f}", "-250.00")
        
        st.markdown("---")
        st.subheader("📊 Projeção de Fluxo de Caixa (Próximos 30 dias)")
        data = {'Dia': pd.to_datetime(pd.date_range(start=datetime.date.today(), periods=30)), 'Projeção': [saldo_caixa + (i * 100) - (i**2 * 2) for i in range(30)]}
        df_projecao = pd.DataFrame(data)
        st.line_chart(df_projecao.rename(columns={'Dia':'index'}).set_index('Dia'))
        
        with st.expander("💡 Alertas e Insights do MaxFinanceiro"):
            st.info("Atenção: se as vendas continuarem nesse ritmo, seu caixa pode ficar negativo em 12 dias.")
            st.success("Sugestão: Crie um combo do seu 'Prato do Dia' (margem alta) com o 'Suco Especial' (margem baixa) para melhorar o lucro geral.")

    # --- 5.2: MaxAdministrativo (Central de Comando) ---
    def exibir_max_administrativo(self):
        st.header("⚙️ MaxAdministrativo")
        st.caption("A Central de Comando para organizar o presente e garantir a conformidade.")

        col1, col2, col3 = st.columns(3)
        col1.metric("Saúde Operacional", "85%", "5%")
        col2.metric("Progresso Estratégico", "62%", "-2%")
        col3.metric("Clima da Equipe", "8.2/10")

        with st.expander("🗂️ Pré-Contabilidade Inteligente", expanded=True):
            st.info("💡 Alerta do Max: Percebi que este mês você não lançou a nota fiscal do seu aluguel. Gostaria de criar um lembrete recorrente?")
            st.dataframe({"Transação": ["Posto Shell", "Venda #1254"], "Categoria (IA)": ["Despesa com Veículo", "Receita de Vendas"]}, use_container_width=True)

        with st.expander("📦 Controle de Estoque e Previsão de Demanda"):
            st.warning("📈 Alerta do Max: Atenção: o Dia das Mães está chegando. Seu estoque do 'Produto Y' não será suficiente.")
            st.progress(75, text="Produto X (75%)")
            st.progress(15, text="Produto Y (15%) - Nível Baixo!")

    # --- 5.3: Central do Cliente 360° ---
    def exibir_central_cliente(self):
        st.header("📈 Central do Cliente 360°")
        st.caption("Transforme dados em relacionamentos e fidelização.")

        col1, col2, col3 = st.columns(3)
        col1.metric("Satisfação (NPS)", "72", "Excelente")
        col2.metric("Taxa de Retenção", "85%")
        col3.metric("Clientes em Risco", "18")

        with st.expander("👥 Segmentação Automática (IA)", expanded=True):
            st.success("Sugestão para 'Campeões': Que tal criar um 'Clube VIP' para seus 8 melhores clientes?")
            st.info("Sugestão para 'Em Risco': Vamos enviar uma campanha de reativação com o título 'Estamos com saudades!'?")

        with st.expander("📝 Análise de Sentimentos da última pesquisa"):
            feedback_data = pd.DataFrame({'Tópico': ['Atendimento', 'Preço', 'Entrega'],'Positivo': [15, 5, 10], 'Negativo': [2, 8, 5]}).set_index('Tópico')
            st.bar_chart(feedback_data)

    # --- 5.4: MaxTrainer IA ---
    def exibir_max_trainer_ia(self):
        st.title("🎓 MaxTrainer IA")
        st.markdown("Seu mentor pessoal para descomplicar a jornada empreendedora.")
        if "messages_trainer" not in st.session_state:
            st.session_state.messages_trainer = [{"role": "assistant", "content": "Olá! Sobre o que vamos conversar hoje? Tente perguntar 'O que é Fluxo de Caixa?' ou 'Explique Análise SWOT'."}]
        
        for message in st.session_state.messages_trainer:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if prompt := st.chat_input("Pergunte sobre DRE, Fluxo de Caixa, Marketing..."):
            st.session_state.messages_trainer.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
            
            with st.chat_message("assistant"):
                with st.spinner("MaxTrainer está pensando..."):
                    # Aqui iria a lógica de chamada da IA, por enquanto, uma resposta simulada
                    full_response = f"Claro! Explicando '{prompt}' usando uma analogia de Futebol... (Esta é uma resposta simulada. A lógica completa da IA seria inserida aqui.)"
                    st.markdown(full_response)
            st.session_state.messages_trainer.append({"role": "assistant", "content": full_response})

    # --- Demais agentes como placeholders ---
    def exibir_max_construtor(self): st.info("🏗️ Agente Max Construtor em desenvolvimento.")
    def exibir_max_marketing_total(self): st.info("🚀 Agente MaxMarketing Total em desenvolvimento.")
    
    # --- Métodos de Onboarding ---
    def exibir_onboarding_calibracao(self):
        st.title("Vamos calibrar o seu Max IA Empresarial! ⚙️")
        with st.form(key="calibration_form"):
            company_name = st.text_input("Nome da Sua Empresa")
            setor = st.selectbox("Setor de Atuação", ["Varejo", "Serviços", "Alimentação", "Outro"])
            if st.form_submit_button("Criar e Continuar"):
                if not company_name: st.warning("O nome da empresa é essencial.")
                else: st.success("Empresa configurada!"); time.sleep(1); st.rerun()

    def exibir_onboarding_trainer(self):
        st.title("Quase lá! Vamos personalizar sua experiência.")
        st.selectbox("Escolha um assunto para analogias:", ["Futebol", "Culinária", "Carros"], key="analogy_choice")
        if st.button("Salvar e Começar a Usar!"): st.success("Preferência salva!"); time.sleep(1); st.rerun()
            
    def exibir_tour_guiado(self):
        st.title("🎉 Bem-vindo ao seu Centro de Comando!")
        if st.button("Entendido, vamos começar!"): st.session_state['start_guided_tour'] = False; st.rerun()


# ==============================================================================
# 6. FUNÇÕES DA INTERFACE DE ENTRADA
# ==============================================================================
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

    if logo_base64: st.markdown(f"<div class='logo-container'><img src='data:image/png;base64,{logo_base64}' width='150'></div>", unsafe_allow_html=True)
    with st.container():
        st.markdown("<div class='main-container'>", unsafe_allow_html=True)
        _ , col, _ = st.columns([1, 2.5, 1])
        with col:
            if st.button("Já sou cliente", use_container_width=True): st.session_state['show_login_form'] = True; st.rerun()
            if st.button("Ainda não sou cliente", type="secondary", use_container_width=True): st.html(f"<script>window.open('{SALES_PAGE_URL}', '_blank')</script>")
            st.caption("<p style='text-align: center; color: white;'>Ao continuar, você aceita nossos Termos e condições.</p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

def exibir_formularios_de_acesso():
    st.markdown("""<style>[data-testid="stSidebar"] { display: none; }</style>""", unsafe_allow_html=True)
    _ , col, _ = st.columns([1, 1.5, 1])
    with col:
        logo_path = get_asset_path('max-ia-lgo.fundo.transparente.png')
        if os.path.exists(logo_path): st.image(logo_path, width=150)
        st.title("Acesse sua Central de Comando")
        tab_login, tab_register = st.tabs(["Login", "Registrar"])
        with tab_login:
            with st.form("login_form_main"):
                email = st.text_input("Email", key="login_email")
                password = st.text_input("Senha", type="password", key="login_pass")
                if st.form_submit_button("Entrar", use_container_width=True):
                    try:
                        user_creds = pb_auth_client.sign_in_with_email_and_password(email, password)
                        st.session_state[f'{APP_KEY_SUFFIX}_user_session_data'] = user_creds
                        st.session_state['show_login_form'] = False; st.rerun()
                    except Exception: st.error("Email ou senha inválidos.")
        with tab_register:
            with st.form("register_form_main"):
                email = st.text_input("Seu Email", key="reg_email")
                password = st.text_input("Crie uma Senha (mínimo 6 caracteres)", type="password", key="reg_pass")
                if st.form_submit_button("Registrar Conta", use_container_width=True):
                    if email and len(password) >= 6:
                        try:
                            new_user = pb_auth_client.create_user_with_email_and_password(email, password)
                            user_data = { "email": email, "registration_date": firebase_admin_firestore.SERVER_TIMESTAMP, "access_level": 2, "analogy_domain": None, "company_id": None }
                            firestore_db.collection(USER_COLLECTION).document(new_user['localId']).set(user_data)
                            st.success("Conta criada! Volte para a aba 'Login' para entrar.")
                        except Exception: st.error("Este e-mail já está em uso ou ocorreu um erro.")
                    else: st.warning("Preencha todos os campos corretamente.")

# ==============================================================================
# 7. ESTRUTURA PRINCIPAL E EXECUÇÃO DO APP
# ==============================================================================
def main():
    if not all([pb_auth_client, firestore_db]):
        st.error("Falha crítica na inicialização dos serviços."); st.stop()

    user_is_authenticated, user_uid, user_email = get_current_user_status(pb_auth_client)

    if user_is_authenticated:
        # USUÁRIO LOGADO - MOSTRA A APLICAÇÃO PRINCIPAL
        st.sidebar.image(get_asset_path('max-ia-lgo.fundo.transparente.png'), width=100)
        st.sidebar.title("Max IA Empresarial")
        st.sidebar.markdown("---")
        
        if 'agente' not in st.session_state:
            llm = get_llm()
            if llm and firestore_db: st.session_state.agente = MaxAgente(llm, firestore_db)
            else: st.error("Agente Max IA não pôde ser inicializado."); st.stop()
        agente = st.session_state.agente
        
        try:
            user_doc = firestore_db.collection(USER_COLLECTION).document(user_uid).get()
            user_data = user_doc.to_dict() if user_doc.exists else None
        except Exception as e: st.error(f"Erro ao buscar dados do usuário: {e}"); st.stop()

        if not user_data: # Segurança extra
            user_data = {"email": user_email, "access_level": 2}
            firestore_db.collection(USER_COLLECTION).document(user_uid).set(user_data, merge=True)
        
        # Lógica de Onboarding simplificada (a lógica completa seria reativada aqui)
        
        st.sidebar.write(f"Logado como: **{user_email}**")
        st.sidebar.caption(f"Nível de Acesso: {user_data.get('access_level', 'N/D')}")
        if st.sidebar.button("Logout", key=f"{APP_KEY_SUFFIX}_logout"):
            st.session_state.clear(); st.rerun()
        
        opcoes_menu = {
            "👋 Bem-vindo": agente.exibir_painel_boas_vindas,
            "💰 MaxFinanceiro": agente.exibir_max_financeiro,
            "⚙️ MaxAdministrativo": agente.exibir_max_administrativo,
            "📈 Central do Cliente 360°": agente.exibir_central_cliente,
            "🚀 MaxMarketing Total": agente.exibir_max_marketing_total,
            "🎓 MaxTrainer IA": agente.exibir_max_trainer_ia,
            "🏗️ MaxConstrutor": agente.exibir_max_construtor,
        }
        
        if user_data.get('access_level') != 1:
            opcoes_a_remover = ["💰 MaxFinanceiro", "⚙️ MaxAdministrativo"]
            for opcao in opcoes_a_remover:
                if opcao in opcoes_menu: del opcoes_menu[opcao]

        selecao_label = st.sidebar.radio("Max Agentes IA:", list(opcoes_menu.keys()), key=f"{APP_KEY_SUFFIX}_menu")
        opcoes_menu[selecao_label]()

    else:
        # USUÁRIO NÃO LOGADO
        if st.session_state.get('show_login_form', False):
            exibir_formularios_de_acesso()
        else:
            exibir_pagina_de_entrada()

if __name__ == "__main__":
    main()
