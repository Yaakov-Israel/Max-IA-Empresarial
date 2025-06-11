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
# ==============================================================================
# 2. CONSTANTES E CARREGAMENTO DE CONFIGURAÇÕES
# ==============================================================================
APP_KEY_SUFFIX = "maxia_app_v9.1_stable"
USER_COLLECTION = "users"
COMPANY_COLLECTION = "companies"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
PROMPTS_CONFIG = carregar_prompts_config()
# ==============================================================================
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
        return io.BytesIO(pdf.output(dest='S').encode('latin-1'))
    return None
# ==============================================================================
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
            st.session_state.update({'user_is_authenticated': True, 'user_uid': uid, 'user_email': email})
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
                            except Exception as e: st.error(f"Ocorreu um erro ao criar sua empresa: {e}")

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
                except Exception as e: st.error(f"Erro ao salvar sua preferência: {e}")

    def exibir_tour_guiado(self):
        st.title("🎉 Bem-vindo ao seu Centro de Comando!")
        st.markdown("Eu sou o Max, seu copiloto de IA. Minha missão é te ajudar a tomar as melhores decisões.")
        st.info("Passei os últimos segundos analisando os dados da sua 'calibração' e preparei a plataforma para você. Note que o menu à esquerda já está disponível.")
        if st.button("Entendido, vamos começar!"):
            st.session_state['start_guided_tour'] = False
            st.rerun()

    def exibir_painel_boas_vindas(self):
        st.markdown("<div style='text-align: center;'><h1>👋 Bem-vindo ao Max IA!</h1></div>", unsafe_allow_html=True)
        logo_base64 = convert_image_to_base64('max-ia-logo.png')
        if logo_base64:
            st.markdown(f"<div style='text-align: center;'><img src='data:image/png;base64,{logo_base64}' width='200'></div>", unsafe_allow_html=True)
        st.markdown("<div style='text-align: center;'><p style='font-size: 1.2em;'>Olá! Eu sou o <strong>Max</strong>, seu assistente de IA para impulsionar o sucesso da sua empresa.</p></div>", unsafe_allow_html=True)
## --- 5.1: MaxMarketing Total --- ##

def get_prompt_campanha(self, nome_campanha, objetivo, publico, produto, duracao, canais, info_adicional):
    return f"""
**Instrução Mestra:** Você é o MaxMarketing Total, um Diretor de Marketing Estratégico especialista em PMEs brasileiras. Sua tarefa é criar um plano de campanha de marketing completo, multicanal e coeso, com base no briefing do usuário.
**Tarefa:** Elabore um plano detalhado, dividindo a resposta em seções claras e bem definidas usando os seguintes marcadores EXATOS: `[ESTRATÉGIA DA CAMPANHA]`, `[CONTEÚDO PARA REDES SOCIAIS]`, `[CONTEÚDO PARA EMAIL MARKETING]` e `[IDEIAS PARA ANÚNCIOS PAGOS]`.

**[BRIEFING DO USUÁRIO]**
- Nome da Campanha: {nome_campanha}
- Principal Objetivo: {objetivo}
- Público-Alvo Detalhado: {publico}
- Produto/Serviço em Foco: {produto}
- Duração da Campanha: {duracao}
- Canais Selecionados: {', '.join(canais)}
- Informações Adicionais: {info_adicional}

**--- INÍCIO DO PLANO DA CAMPANHA ---**
[ESTRATÉGIA DA CAMPANHA]
* **Conceito Central:** (Crie um conceito criativo, o "Big Idea" da campanha em uma frase).
* **Mensagem Principal:** (Qual a mensagem chave que será repetida em todos os canais?).
* **Linha do Tempo Sugerida:** (Divida a duração da campanha em fases. Ex: Semana 1: Teaser...).
* **KPIs para Monitoramento:** (Sugira 2-3 métricas para medir o sucesso. Ex: Taxa de Cliques, Custo por Lead).
[CONTEÚDO PARA REDES SOCIAIS]
(Crie 3 posts diferentes para o Instagram/Facebook que sigam a linha do tempo da campanha).
* **Post 1 (Fase de Teaser):**
* **Post 2 (Fase de Engajamento):**
* **Post 3 (Fase de Oferta/CTA):**
[CONTEÚDO PARA EMAIL MARKETING]
(Crie uma sequência de 2 e-mails).
* **E-mail 1 (Apresentação):**
* **E-mail 2 (Lembrete/Oferta):**
[IDEIAS PARA ANÚNCIOS PAGOS]
(Crie 2 sugestões de texto para anúncios).
* **Anúncio 1 (Foco em Dor/Solução):**
* **Anúncio 2 (Foco em Oferta/Benefício):**
"""

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
                            if "OLX" in formato_selecionado or "Mercado Livre" in formato_selecionado:
                                especialista = "um vendedor experiente de marketplaces."
                                tarefa = "Crie um anúncio otimizado. Gere um Título chamativo (máx 60 caracteres) e uma Descrição detalhada e persuasiva."
                            elif "Shopify" in formato_selecionado or "E-commerce" in formato_selecionado:
                                especialista = "um especialista em copywriting para e-commerce."
                                tarefa = "Crie uma descrição de produto completa e otimizada para SEO. Gere um Título de Produto claro, uma Descrição Persuasiva e 3 a 5 bullet points."
                            elif "Blog" in formato_selecionado:
                                especialista = "um especialista em SEO e Marketing de Conteúdo."
                                tarefa = "Crie um post de blog otimizado para gerar leads. Estruture com um Título magnético, uma introdução que prenda a atenção, desenvolva o tema com subtítulos e parágrafos curtos, e finalize com uma conclusão e um CTA claro para o leitor tomar uma ação."
                            else:
                                especialista = "um especialista de marketing digital."
                                tarefa = f"Crie um conteúdo para **{formato_selecionado}**."
                            prompt_final = f"**Instrução:** Você é {especialista}\n\n**Tarefa:** {tarefa}\n\n{instrucao_base}"
                            try:
                                if self.llm: resposta = self.llm.invoke(prompt_final); st.session_state[session_key_post] = resposta.content; st.rerun()
                                else: st.error("LLM não disponível.")
                            except Exception as e: st.error(f"Erro na IA: {e}")
    
    elif acao_selecionada == "Criar campanha completa":
        st.session_state[session_key_post] = None
        if st.session_state[session_key_campaign]:
            st.subheader("🎉 Plano de Campanha Gerado pelo Max IA!")
            resposta_completa = st.session_state[session_key_campaign]
            with st.expander("📥 Baixar Plano de Campanha Completo"):
                formato_campanha = st.selectbox("Escolha o formato:", ("txt", "docx", "pdf"), key="dl_fmt_campaign")
                st.download_button(label=f"Baixar como .{formato_campanha}",data=gerar_arquivo_download(resposta_completa, formato_campanha),file_name=f"plano_de_campanha_max_ia.{formato_campanha}",use_container_width=True)
            st.markdown("---")
            def extrair_secao(texto_completo, secao_inicio, todas_secoes):
                try:
                    idx_inicio = texto_completo.index(secao_inicio) + len(secao_inicio); idx_fim = len(texto_completo)
                    secao_atual_index = todas_secoes.index(secao_inicio)
                    if secao_atual_index + 1 < len(todas_secoes):
                        proxima_secao = todas_secoes[secao_atual_index + 1]
                        if proxima_secao in texto_completo: idx_fim = texto_completo.index(proxima_secao)
                    return texto_completo[idx_inicio:idx_fim].strip()
                except ValueError: return f"A seção '{secao_inicio}' não foi encontrada na resposta."
            secoes = ["[ESTRATÉGIA DA CAMPANHA]", "[CONTEÚDO PARA REDES SOCIAIS]", "[CONTEÚDO PARA EMAIL MARKETING]", "[IDEIAS PARA ANÚNCIOS PAGOS]"]
            conteudo_estrategia = extrair_secao(resposta_completa, secoes[0], secoes)
            conteudo_redes = extrair_secao(resposta_completa, secoes[1], secoes)
            conteudo_email = extrair_secao(resposta_completa, secoes[2], secoes)
            conteudo_anuncios = extrair_secao(resposta_completa, secoes[3], secoes)
            tab1, tab2, tab3, tab4 = st.tabs(["🧭 Estratégia", "📱 Redes Sociais", "✉️ E-mail", "💰 Anúncios"])
            with tab1: st.markdown(conteudo_estrategia)
            with tab2: st.markdown(conteudo_redes)
            with tab3: st.markdown(conteudo_email)
            with tab4: st.markdown(conteudo_anuncios)
            st.markdown("---")
            if st.button("✨ Criar Nova Campanha"): st.session_state[session_key_campaign] = None; st.rerun()
        else:
            st.subheader("📝 Briefing da Campanha Estratégica")
            with st.form(key=f"mkt_form_campaign_{APP_KEY_SUFFIX}"):
                st.write("Preencha os detalhes para o Max IA construir seu plano de campanha.")
                nome_campanha = st.text_input("1. Nome da Campanha")
                objetivo_campanha = st.text_area("2. Principal Objetivo")
                publico_campanha = st.text_area("3. Público-alvo (dores e desejos)")
                produto_servico_campanha = st.text_area("4. Produto/Serviço em foco")
                duracao_campanha = st.selectbox("5. Duração:", ("1 Semana", "15 Dias", "1 Mês", "Trimestre"))
                novos_canais = ["Instagram", "Facebook", "E-mail Marketing", "Google ADS", "Vídeo YouTube", "Vídeo TikTok", "Reels Facebook", "Reels Instagram", "Blog"]
                canais_campanha = st.multiselect("6. Canais:", options=novos_canais, placeholder="Escolha as opções desejadas")
                info_adicional_campanha = st.text_area("7. Informações adicionais ou ofertas")
                if st.form_submit_button("🚀 Gerar Plano de Campanha"):
                    if not all([nome_campanha, objetivo_campanha, publico_campanha, produto_servico_campanha]):
                        st.warning("Preencha os 4 primeiros campos.")
                    else:
                        with st.spinner("🧠 Max IA está pensando como um estrategista..."):
                            prompt_campanha = self.get_prompt_campanha(nome_campanha, objetivo_campanha, publico_campanha, produto_servico_campanha, duracao_campanha, canais_campanha, info_adicional_campanha)
                            try:
                                if self.llm:
                                    resposta_ia = self.llm.invoke(prompt_campanha)
                                    st.session_state[session_key_campaign] = resposta_ia.content; st.rerun()
                                else:
                                    st.error("LLM não disponível.")
                            except Exception as e:
                                st.error(f"Erro na IA: {e}")
## --- 5.2: Max Construtor - Página de Venda --- ##
def exibir_max_construtor(self):
    st.info("Agente Max Construtor em desenvolvimento.")
## --- 5.3: Max Financeiro - O Cérebro Financeiro em Tempo Real --- ##
def exibir_max_financeiro(self):
    st.info("Agente Max Financeiro em desenvolvimento.")
## --- 5.4: Max Administrativo - Central de Comando, Estratégia e Operações --- ##
def exibir_max_administrativo(self):
    st.info("Agente Max Administrativo em desenvolvimento.")
## --- 5.5: MaxTrainer IA - Mentor Empresarial --- ##
def get_analogy_prompt(self, user_question, analogy_domain):
    return f"""
**Instrução Mestra:** Você é o MaxTrainer IA, um mentor de negócios amigável, paciente e genial. Sua especialidade é explicar conceitos de negócios complexos usando analogias simples e detalhadas.

**Contexto:**
- **Domínio de Analogia do Usuário:** {analogy_domain}
- **Pergunta do Usuário:** {user_question}

**Sua Tarefa em 3 Passos:**
1.  **Identifique o Conceito Central:** Entenda qual é o conceito de negócios principal por trás da pergunta do usuário.
2.  **Busque a Definição Factual:** Internamente, pense na definição técnica e correta do conceito.
3.  **Crie a Resposta com Analogia:** Responda ao usuário EXCLUSIVAMENTE usando uma analogia detalhada baseada no DOMÍNIO DE ANALOGIA dele. Não use jargões de negócios. Seja didático, divertido e profundo. Comece a resposta de forma amigável.

**Exemplo (se o domínio fosse 'culinária' e a pergunta 'O que é SWOT?'):**
"Ótima pergunta! Pensar em SWOT é como planejar um grande jantar.
- **Forças:** São seus 'ingredientes secretos', o que sua cozinha faz de melhor. Ex: O tempero especial da sua avó que ninguém copia.
- **Fraquezas:** É aquele prato que sempre queima. Ex: Seu forno não assa direito.
- **Oportunidades:** São as tendências lá fora. Ex: Seus vizinhos amariam receber marmitas.
- **Ameaças:** É a nova padaria chique que abriu na sua rua."

**--- INÍCIO DA RESPOSTA ---**
"""

def exibir_max_trainer_ia(self):
    st.title("🎓 MaxTrainer IA")
    st.markdown("Seu mentor pessoal para descomplicar a jornada empreendedora. Faça qualquer pergunta de negócios!")

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
            with st.spinner("MaxTrainer está pensando na melhor analogia para você..."):
                try:
                    user_uid = st.session_state.get('user_uid')
                    user_doc = self.db.collection(USER_COLLECTION).document(user_uid).get()
                    analogy_domain = user_doc.to_dict().get("analogy_domain", "negócios")
                    
                    final_prompt = self.get_analogy_prompt(prompt, analogy_domain)
                    
                    if self.llm:
                        full_response = self.llm.invoke(final_prompt).content
                    else:
                        full_response = "Desculpe, meu cérebro (LLM) não está disponível agora."
                        
                except Exception as e:
                    full_response = f"Ocorreu um erro ao processar sua pergunta: {e}"
            
            message_placeholder.markdown(full_response)
        st.session_state.messages_trainer.append({"role": "assistant", "content": full_response})
# 5.6: Central do Cliente 360°
def exibir_central_cliente(self):
    st.info("Agente Central do Cliente 360° em desenvolvimento.")
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
            else:
                st.error("Agente Max IA não pôde ser inicializado."); st.stop()
        
        agente = st.session_state.agente
        
        try:
            user_doc_ref = firestore_db.collection(USER_COLLECTION).document(user_uid)
            user_doc = user_doc_ref.get()
            user_data = user_doc.to_dict() if user_doc.exists else None
        except Exception as e:
            st.error(f"Erro ao buscar dados do usuário: {e}"); user_data = None; st.stop()

        if not user_data:
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
                    st.sidebar.markdown("---")
                    st.sidebar.write(f"Logado como: **{user_email}**")
                    if st.sidebar.button("Logout", key=f"{APP_KEY_SUFFIX}_logout"):
                        st.session_state.clear(); st.rerun()
                    
                    opcoes_menu = {
                        "👋 Bem-vindo": agente.exibir_painel_boas_vindas,
                        "🚀 MaxMarketing Total": agente.exibir_max_marketing_total,
                        "🎓 MaxTrainer IA": agente.exibir_max_trainer_ia,
                        "📈 Central do Cliente 360°": agente.exibir_central_cliente,
                        "⚙️ MaxAdministrativo": agente.exibir_max_administrativo,
                        "💰 MaxFinanceiro": agente.exibir_max_financeiro,
                        "🏗️ MaxConstrutor": agente.exibir_max_construtor,
                    }
                    selecao_label = st.sidebar.radio("Max Agentes IA:", list(opcoes_menu.keys()), key=f"{APP_KEY_SUFFIX}_menu")
                    opcoes_menu[selecao_label]()
            else:
                agente.exibir_onboarding_trainer()
        else:
            agente.exibir_onboarding_calibracao()
    else:
        # --- BLOCO DE LOGIN E REGISTRO ---
        st.title("🔑 Bem-vindo ao Max IA")
        st.info("Faça login ou registre-se na barra lateral.")
        auth_action = st.sidebar.radio("Acesso:", ["Login", "Registrar"], key=f"{APP_KEY_SUFFIX}_auth")
        if auth_action == "Login":
            with st.sidebar.form("login_form"):
                email = st.text_input("Email")
                password = st.text_input("Senha", type="password")
                if st.form_submit_button("Entrar"):
                    try:
                        user_creds = pb_auth_client.sign_in_with_email_and_password(email, password)
                        st.session_state[f'{APP_KEY_SUFFIX}_user_session_data'] = user_creds
                        st.rerun()
                    except Exception: st.sidebar.error("Erro no login.")
        else: 
            with st.sidebar.form("register_form"):
                email = st.text_input("Seu Email")
                password = st.text_input("Crie uma Senha", type="password")
                if st.form_submit_button("Registrar Conta"):
                    if email and len(password) >= 6:
                        try:
                            new_user = pb_auth_client.create_user_with_email_and_password(email, password)
                            user_data = {"email": email, "registration_date": firebase_admin.firestore.SERVER_TIMESTAMP, "analogy_domain": None, "company_id": None}
                            firestore_db.collection(USER_COLLECTION).document(new_user['localId']).set(user_data)
                            st.sidebar.success("Conta criada! Faça o login.")
                        except Exception as e: st.sidebar.error("E-mail já em uso ou erro no registro.")
                    else: st.sidebar.warning("Preencha todos os campos corretamente.")
    
    st.sidebar.markdown("---")
    st.sidebar.info("Max IA | by Yaakov Israel & Gemini AI")

if __name__ == "__main__":
    main()
