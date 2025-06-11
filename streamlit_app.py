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
            company_name = st.text_input("Nome da Empresa", placeholder="Ex: Restaurante Sabor Divino")
            setor = st.selectbox("Setor de Atuação", ["Varejo", "Serviços", "Indústria", "Saúde", "TI", "Alimentação", "Outro"])
            porte = st.selectbox("Porte da Empresa", ["MEI", "Microempresa (ME)", "Empresa de Pequeno Porte (EPP)"])
            st.subheader("2. Desafios e Metas")
            desafio_principal = st.selectbox("Qual é o seu maior desafio na gestão hoje?", 
                                             ["Não sei para onde meu dinheiro vai", "Tenho dificuldade em precificar", "Meu fluxo de caixa está sempre apertado", "Perco muito tempo com tarefas manuais", "Outro"])
            submitted = st.form_submit_button("Finalizar Calibração e Construir meu Centro de Comando!")
            if submitted:
                if not company_name:
                    st.warning("O nome da empresa é essencial.")
                else:
                    user_uid = st.session_state.get('user_uid')
                    if user_uid and self.db:
                        with st.spinner("Analisando seus dados e configurando sua plataforma..."):
                            try:
                                company_ref = self.db.collection('companies').document()
                                company_data = {
                                    "company_name": company_name, "owner_uid": user_uid, "setor": setor, 
                                    "porte": porte, "desafio_principal": desafio_principal,
                                    "created_at": firebase_admin.firestore.SERVER_TIMESTAMP
                                }
                                company_ref.set(company_data)
                                user_ref = self.db.collection(USER_COLLECTION).document(user_uid)
                                user_ref.update({"company_id": company_ref.id})
                                st.success(f"Calibração concluída! O Max IA agora entende melhor a '{company_name}'.")
                                time.sleep(2)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Ocorreu um erro ao calibrar sua empresa: {e}")

    def exibir_onboarding_trainer(self):
        st.title("Quase lá! Vamos personalizar sua experiência.")
        st.markdown("Para que suas interações com o Max IA sejam perfeitas, me conte sobre um assunto que você gosta. Assim, posso te explicar os conceitos mais complexos de negócios de um jeito que faça sentido para você.")
        opcoes_analogia = ["Futebol", "Culinária", "Carros", "Cinema e Séries", "Música", "Moda", "Negócios (tradicional)"]
        dominio_escolhido = st.selectbox("Para que eu possa te explicar tudo de um jeito que faça sentido para você, escolha um assunto abaixo:", opcoes_analogia, key="analogy_choice")
        if st.button("Salvar e Continuar", key="save_analogy_domain"):
            user_uid = st.session_state.get('user_uid')
            if user_uid and self.db:
                try:
                    user_ref = self.db.collection(USER_COLLECTION).document(user_uid)
                    user_ref.update({"analogy_domain": dominio_escolhido.lower()})
                    st.success(f"Ótima escolha! Agora vamos falar a mesma língua. Redirecionando...")
                    time.sleep(2)
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar sua preferência: {e}")

    def exibir_painel_boas_vindas(self):
        st.markdown("<div style='text-align: center;'><h1>👋 Bem-vindo ao Max IA!</h1></div>", unsafe_allow_html=True)
        logo_base64 = convert_image_to_base64('max-ia-logo.png')
        if logo_base64:
            st.markdown(f"<div style='text-align: center;'><img src='data:image/png;base64,{logo_base64}' width='200'></div>", unsafe_allow_html=True)
        st.markdown("<div style='text-align: center;'><p style='font-size: 1.2em;'>Olá! Eu sou o <strong>Max</strong>, seu assistente de IA para impulsionar o sucesso da sua empresa.</p></div>", unsafe_allow_html=True)

    ## --- SUB-MÓDULO 5.1: MaxMarketing Total --- ##
    def get_prompt_campanha(self, nome_campanha, objetivo, publico, produto, duracao, canais, info_adicional):
        return f"""
**Instrução Mestra:** Você é o MaxMarketing Total, um Diretor de Marketing Estratégico especialista em PMEs brasileiras...
""" # (O prompt completo continua aqui)
    def exibir_max_marketing_total(self):
        st.header("🚀 MaxMarketing Total"); st.caption("Seu copiloto para criar posts, campanhas completas e muito mais!")
        st.markdown("---")
        session_key_post = f"mkt_post_{APP_KEY_SUFFIX}"
        if session_key_post not in st.session_state: st.session_state[session_key_post] = None
        session_key_campaign = f"mkt_campaign_{APP_KEY_SUFFIX}"
        if session_key_campaign not in st.session_state: st.session_state[session_key_campaign] = None
        opcoes_marketing = ["Criar Post", "Criar campanha completa"]
        acao_selecionada = st.radio("Qual ferramenta do MaxMarketing vamos usar hoje?", opcoes_marketing, key=f"mkt_radio_{APP_KEY_SUFFIX}")
        if acao_selecionada == "Criar Post":
            st.session_state[session_key_campaign] = None
            if st.session_state[session_key_post]:
                st.subheader("🎉 Conteúdo Gerado pelo Max IA!")
                st.markdown(st.session_state[session_key_post])
                st.markdown("---")
                with st.expander("📥 Baixar Conteúdo"):
                    formato = st.selectbox("Formato:", ("txt", "docx", "pdf"), key=f"dl_fmt_post_{APP_KEY_SUFFIX}")
                    st.download_button(f"Baixar .{formato}", gerar_arquivo_download(st.session_state[session_key_post], formato), f"post_max_ia.{formato}", use_container_width=True)
                st.markdown("---")
                if st.button("✨ Criar Outro Conteúdo"): st.session_state[session_key_post] = None; st.rerun()
            else:
                st.subheader("📝 Briefing do Conteúdo")
                with st.form(key=f"mkt_form_post_{APP_KEY_SUFFIX}"):
                    formatos_disponiveis = ["Post para Blog (Gerar Leads)","Anúncio para OLX / Mercado Livre", "Descrição de Produto para Shopify / E-commerce","Instagram Post (Feed)", "Instagram Stories", "Instagram Reels (Roteiro)","Facebook Post", "Facebook Stories","Mensagem para WhatsApp", "E-mail Marketing", "Google ADS (Texto)","Roteiro de Vídeo YouTube", "Roteiro para TikTok", "Post para X (Twitter)"]
                    formato_selecionado = st.selectbox("1. Escolha o formato do conteúdo:", formatos_disponiveis)
                    objetivo = st.text_area("2. Qual o objetivo deste conteúdo?")
                    publico = st.text_input("3. Quem você quer alcançar?")
                    produto_servico = st.text_area("4. Qual produto/serviço está promovendo?")
                    info_adicional = st.text_area("5. Alguma informação adicional ou CTA?")
                    if st.form_submit_button("💡 Gerar Conteúdo com Max IA!"):
                        if not objetivo: st.warning("O objetivo é essencial.")
                        else:
                            with st.spinner(f"🤖 Max IA está pensando como um especialista em {formato_selecionado}..."):
                                instrucao_base = f"**Contexto do Negócio:**\n- **Objetivo:** {objetivo}\n- **Público-alvo:** {publico}\n- **Produto/Serviço:** {produto_servico}\n- **Informações Adicionais/CTA:** {info_adicional}"
                                if "OLX" in formato_selecionado or "Mercado Livre" in formato_selecionado: especialista = "um vendedor experiente de marketplaces..."
                                elif "Shopify" in formato_selecionado or "E-commerce" in formato_selecionado: especialista = "um especialista em copywriting para e-commerce..."
                                elif "Blog" in formato_selecionado: especialista = "um especialista em SEO e Marketing de Conteúdo..."
                                else: especialista = "um especialista de marketing digital..."; tarefa = f"Crie um conteúdo para **{formato_selecionado}**."
                                prompt_final = f"**Instrução:** Você é {especialista}\n\n**Tarefa:** {tarefa}\n\n{instrucao_base}"
                                try:
                                    if self.llm: resposta = self.llm.invoke(prompt_final); st.session_state[session_key_post] = resposta.content; st.rerun()
                                    else: st.error("LLM não disponível.")
                                except Exception as e: st.error(f"Erro na IA: {e}")
        elif acao_selecionada == "Criar campanha completa":
            pass # (código da campanha aqui)

    ## --- SUB-MÓDULOS 5.2, 5.3, 5.4 (Placeholders) --- ##
    def exibir_max_construtor(self): st.info("Agente Max Construtor em desenvolvimento.")
    def exibir_max_financeiro(self): st.info("Agente Max Financeiro em desenvolvimento.")
    def exibir_max_administrativo(self): st.info("Agente Max Administrativo em desenvolvimento.")

    ## --- SUB-MÓDULO 5.5: MaxTrainer IA --- ##
    def get_analogy_prompt(self, user_question, analogy_domain):
        return f"""
**Instrução Mestra:** Você é o MaxTrainer IA, um mentor de negócios amigável...
""" # (O prompt completo continua aqui)
    def exibir_max_trainer_ia(self):
        st.title("🎓 MaxTrainer IA")
        st.markdown("Seu mentor pessoal para descomplicar a jornada empreendedora...")
        if "messages_trainer" not in st.session_state:
            st.session_state.messages_trainer = [{"role": "assistant", "content": "Olá! Sobre o que vamos conversar hoje?"}]
        for message in st.session_state.messages_trainer:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        if prompt := st.chat_input("Pergunte sobre DRE, Fluxo de Caixa, Marketing..."):
            st.session_state.messages_trainer.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                with st.spinner("MaxTrainer está pensando..."):
                    try:
                        user_uid = st.session_state.get('user_uid')
                        user_doc = self.db.collection(USER_COLLECTION).document(user_uid).get()
                        analogy_domain = user_doc.to_dict().get("analogy_domain", "negócios")
                        final_prompt = self.get_analogy_prompt(prompt, analogy_domain)
                        if self.llm:
                            full_response = self.llm.invoke(final_prompt).content
                        else:
                            full_response = "LLM não disponível."
                    except Exception as e:
                        full_response = f"Erro: {e}"
                    message_placeholder.markdown(full_response)
            st.session_state.messages_trainer.append({"role": "assistant", "content": full_response})
# ==============================================================================
# 6. ESTRUTURA PRINCIPAL E EXECUÇÃO DO APP
# ==============================================================================
def main():
    if not all([pb_auth_client, firestore_db, PROMPTS_CONFIG]):
        st.error("Falha crítica na inicialização dos serviços. A aplicação não pode continuar.")
        st.stop()

    user_is_authenticated, user_uid, user_email = get_current_user_status(pb_auth_client)

    if user_is_authenticated:
        llm = get_llm()
        if 'agente' not in st.session_state and llm and firestore_db:
            st.session_state.agente = MaxAgente(llm, firestore_db)
        
        agente = st.session_state.get('agente')
        if agente:
            try:
                user_doc_ref = firestore_db.collection(USER_COLLECTION).document(user_uid)
                user_doc = user_doc_ref.get()
                if user_doc.exists:
                    user_data = user_doc.to_dict()
                else:
                    user_data = {} 
                    user_doc_ref.set({
                        "email": user_email, 
                        "registration_date": firebase_admin.firestore.SERVER_TIMESTAMP, 
                        "analogy_domain": None,
                        "company_id": None
                    })
            except Exception as e:
                st.error(f"Erro ao buscar dados do usuário: {e}")
                user_data = None
                st.stop()

            # --- LÓGICA DE ONBOARDING EM 2 ETAPAS ---
            
            # Etapa 1: O usuário está vinculado a uma empresa?
            if user_data and user_data.get("company_id"):
                
                # Etapa 2: Se tem empresa, ele já escolheu a analogia?
                if user_data.get("analogy_domain"):
                    # TUDO CERTO! MOSTRA A APLICAÇÃO PRINCIPAL
                    st.sidebar.title("Max IA")
                    st.sidebar.markdown("Seu Centro de Comando Inteligente")
                    st.sidebar.markdown("---")
                    st.sidebar.write(f"Logado como: **{user_email}**")

                    if st.sidebar.button("Logout", key=f"{APP_KEY_SUFFIX}_logout"):
                        for k in list(st.session_state.keys()): del st.session_state[k]
                        st.rerun()

                    opcoes_menu = {
                        "👋 Bem-vindo": agente.exibir_painel_boas_vindas,
                        "🚀 MaxMarketing Total": agente.exibir_max_marketing_total,
                        "🎓 MaxTrainer IA": agente.exibir_max_trainer_ia,
                    }
                    selecao_label = st.sidebar.radio("Max Agentes IA:", list(opcoes_menu.keys()), key=f"main_nav_{APP_KEY_SUFFIX}")
                    opcoes_menu[selecao_label]()
                else:
                    # Se tem empresa mas não analogia, mostra o onboarding do trainer.
                    agente.exibir_onboarding_trainer()
            else:
                # Se não tem empresa, mostra o onboarding de calibração.
                agente.exibir_onboarding_calibracao()
        else:
            st.error("Agente Max IA não pôde ser carregado.")
    else:
        # --- BLOCO DE LOGIN E REGISTRO (JÁ CORRIGIDO) ---
        st.title("🔑 Bem-vindo ao Max IA")
        st.info("Faça login ou registre-se na barra lateral para começar.")
        logo_base64 = convert_image_to_base64('max-ia-logo.png')
        if logo_base64: st.image(f"data:image/png;base64,{logo_base64}", width=200)

        auth_action = st.sidebar.radio("Acesso:", ["Login", "Registrar"], key=f"{APP_KEY_SUFFIX}_auth_choice")
        if auth_action == "Login":
            with st.sidebar.form(f"{APP_KEY_SUFFIX}_login_form"):
                email = st.text_input("Email")
                password = st.text_input("Senha", type="password")
                if st.form_submit_button("Entrar"):
                    try:
                        user_creds = pb_auth_client.sign_in_with_email_and_password(email, password)
                        st.session_state[f'{APP_KEY_SUFFIX}_user_session_data'] = dict(user_creds)
                        st.rerun()
                    except Exception:
                        st.sidebar.error("Erro no login. Verifique as credenciais.")
        else: 
            with st.sidebar.form(f"{APP_KEY_SUFFIX}_register_form"):
                email = st.text_input("Seu Email")
                password = st.text_input("Crie uma Senha (mín. 6 caracteres)", type="password")
                if st.form_submit_button("Registrar Conta"):
                    if email and len(password) >= 6:
                        try:
                            new_user = pb_auth_client.create_user_with_email_and_password(email, password)
                            user_data = {
                                "email": email,
                                "registration_date": firebase_admin.firestore.SERVER_TIMESTAMP,
                                "analogy_domain": None,
                                "company_id": None
                            }
                            firestore_db.collection(USER_COLLECTION).document(new_user['localId']).set(user_data, merge=True)
                            st.sidebar.success("Conta criada! Por favor, faça o login.")
                        except Exception as e:
                            st.sidebar.error("E-mail já em uso ou erro no registro.")
                    else:
                        st.sidebar.warning("Preencha todos os campos corretamente.")
    
    st.sidebar.markdown("---")
    st.sidebar.info("Max IA | by Yaakov Israel & Gemini AI")

if __name__ == "__main__":
    main()
