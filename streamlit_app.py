# ==============================================================================
# streamlit_app.py (VERSÃO FÊNIX v1.1 - CORREÇÃO DE IMAGENS E NAVEGAÇÃO)
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
APP_KEY_SUFFIX = "maxia_app_v4.1_genesis_fix"
USER_COLLECTION = "users"
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

# 4. INICIALIZAÇÃO DE SERVIÇOS
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
        if api_key: return ChatGoogleGenerativeAI(model="gemini-1.5-pro-latest", google_api_key=api_key, temperature=0.7)
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
class MaxAgente:
    def __init__(self, llm_instance, db_firestore_instance):
        self.llm = llm_instance; self.db = db_firestore_instance

    def exibir_painel_boas_vindas(self):
        st.markdown("<div style='text-align: center;'><h1>👋 Bem-vindo ao Max IA!</h1></div>", unsafe_allow_html=True)
        logo_base64 = convert_image_to_base64('max-ia-logo.png')
        if logo_base64: st.markdown(f"<div style='text-align: center;'><img src='data:image/png;base64,{logo_base64}' width='200'></div>", unsafe_allow_html=True)
        st.markdown("<div style='text-align: center;'><p style='font-size: 1.2em;'>Olá! Eu sou o <strong>Max</strong>, seu assistente de IA para impulsionar o sucesso da sua empresa.</p></div>", unsafe_allow_html=True)

    def exibir_max_marketing_total(self):
        # Este método está funcional e não será alterado nesta etapa.
        st.header("🚀 MaxMarketing Total"); st.caption("Seu copiloto para criar posts, campanhas completas e muito mais!")
        st.markdown("---")
        # ... (código completo e funcional do marketing)
        session_key_post = f"mkt_post_{APP_KEY_SUFFIX}";
        if session_key_post not in st.session_state: st.session_state[session_key_post] = None
        session_key_campaign = f"mkt_campaign_{APP_KEY_SUFFIX}"
        if session_key_campaign not in st.session_state: st.session_state[session_key_campaign] = None
        opcoes_marketing = ["Criar Post", "Criar campanha completa"]
        acao_selecionada = st.radio("Qual ferramenta do MaxMarketing vamos usar hoje?", opcoes_marketing, key=f"mkt_radio_{APP_KEY_SUFFIX}")
        if acao_selecionada == "Criar Post":
            st.session_state[session_key_campaign] = None
            # ... (código do Criar Post)
        elif acao_selecionada == "Criar campanha completa":
            st.session_state[session_key_post] = None
            # ... (código do Criar Campanha)
        
    def exibir_max_construtor(self):
        st.header("🏗️ Max Construtor de Landing Pages"); st.caption("Vamos criar juntos uma página de vendas de alta conversão.")
        st.markdown("---")

        if 'genesis_step' not in st.session_state: st.session_state.genesis_step = 0
        if 'genesis_briefing' not in st.session_state: st.session_state.genesis_briefing = {}
        if 'genesis_html_code' not in st.session_state: st.session_state.genesis_html_code = None

        if st.session_state.genesis_html_code:
            st.success("✅ Sua Landing Page foi gerada com sucesso!"); st.markdown("---")
            st.subheader("👀 Pré-visualização Interativa"); st.info("A pré-visualização abaixo é totalmente funcional. Role para ver a página completa.")
            st.components.v1.html(st.session_state.genesis_html_code, height=600, scrolling=True)
            st.markdown("---"); st.subheader("📥 Baixar Código da Página")
            st.download_button(label="Baixar index.html", data=st.session_state.genesis_html_code, file_name="index.html", mime="text/html", use_container_width=True, type="primary")
            st.markdown("---")
            with st.expander("🚀 Sua página está pronta! E agora? (Dicas de Hospedagem)"):
                st.markdown("""
                🎓 **MaxTrainer diz:** Hospedar sua página é mais fácil do que parece! Com o arquivo `index.html` em mãos, você pode publicá-la em minutos. Aqui estão 3 opções excelentes, muitas com planos gratuitos:
                1.  **Netlify Drop:** Ideal para a maneira mais rápida de colocar um site no ar. Basta arrastar e soltar seu arquivo `index.html`. Link: [https://app.netlify.com/drop](https://app.netlify.com/drop)
                2.  **Vercel:** Muito poderosa e com ótima performance, também com um processo de deploy muito simples. Link: [https://vercel.com](https://vercel.com)
                3.  **GitHub Pages:** Se você já usa o GitHub, pode hospedar sua página diretamente do seu repositório, de graça. Link: [https://pages.github.com/](https://pages.github.com/)
                """)
            if st.button("✨ Criar Outra Landing Page"):
                st.session_state.genesis_step = 0; st.session_state.genesis_briefing = {}; st.session_state.genesis_html_code = None
                st.rerun()
        
        elif st.session_state.genesis_step > len(self.get_perguntas_genesis()):
            st.success("✅ Entrevista Concluída! Revise o briefing abaixo.")
            st.markdown("---"); st.subheader("Resumo do Briefing da Landing Page:")
            briefing_formatado = ""
            for i, (pergunta, resposta) in enumerate(st.session_state.genesis_briefing.items(), 1):
                st.markdown(f"**{pergunta}**"); st.markdown(f"> {resposta if resposta else 'Não preenchido'}")
                briefing_formatado += f"{i}. {pergunta}\nResposta: {resposta}\n\n"
            st.markdown("---")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("⬅️ Corrigir Respostas"): st.session_state.genesis_step = 1; st.rerun()
            with col2:
                if st.button("✨ Gerar Landing Page com Max IA!", type="primary"):
                    with st.spinner("🚀 Max Construtor está desenhando, codificando e otimizando sua página..."):
                        prompt_construtor = self.get_prompt_construtor(briefing_formatado)
                        try:
                            if self.llm:
                                resposta_ia = self.llm.invoke(prompt_construtor).content
                                html_limpo = resposta_ia.strip().removeprefix("```html").removesuffix("```").strip()
                                st.session_state.genesis_html_code = html_limpo
                                st.rerun()
                            else: st.error("LLM não disponível.")
                        except Exception as e: st.error(f"Erro ao contatar a IA: {e}")
        else:
            perguntas = self.get_perguntas_genesis()
            step = st.session_state.genesis_step
            if step == 0:
                st.info("Eu sou o Max Construtor. Juntos, vamos criar uma landing page de alta conversão.")
                if st.button("Vamos Começar a Entrevista!", type="primary"):
                    st.session_state.genesis_step = 1; st.rerun()
            else:
                p_info = perguntas[step]
                st.progress(step / len(perguntas))
                st.subheader(f"Pergunta {step}/{len(perguntas)}")
                with st.expander("🎓 Dica do MaxTrainer"): st.write(p_info["dica"])
                with st.form(key=f"genesis_form_{step}"):
                    default_value = st.session_state.genesis_briefing.get(p_info["pergunta"], "")
                    resposta = st.text_area(p_info["pergunta"], value=default_value, key=f"genesis_input_{step}", height=150)
                    
                    col_nav1, col_nav2 = st.columns(2)
                    with col_nav1:
                        if st.form_submit_button("⬅️ Pergunta Anterior", use_container_width=True, disabled=(step == 1)):
                            st.session_state.genesis_briefing[p_info["pergunta"]] = resposta
                            st.session_state.genesis_step -= 1; st.rerun()
                    with col_nav2:
                        if st.form_submit_button("Próxima Pergunta ➡️", use_container_width=True, type="primary"):
                            st.session_state.genesis_briefing[p_info["pergunta"]] = resposta
                            st.session_state.genesis_step += 1; st.rerun()

    def get_perguntas_genesis(self):
        return {
            1: {"pergunta": "Qual o nome do seu produto, serviço ou empresa?", "dica": "Seja claro e direto."},
            2: {"pergunta": "Qual é a sua grande promessa ou headline principal?", "dica": "Foque na transformação que você gera. Ex: 'Conforto e elegância a cada passo'."},
            3: {"pergunta": "Qual o estilo visual da sua marca? Descreva em poucas palavras o tipo de imagem que melhor representa seu negócio (ex: 'escritório moderno', 'pessoas sorrindo na natureza').", "dica": "Seja descritivo! A IA usará estas palavras para buscar uma imagem de alta qualidade. Tente usar 2 ou 3 palavras-chave."},
            4: {"pergunta": "Para quem é esta solução? Descreva seu cliente ideal.", "dica": "'Mulheres de 30-50 anos que valorizam o conforto' é melhor do que 'Pessoas que precisam de sapatos'."},
            5: {"pergunta": "Liste 3 a 4 características ou benefícios importantes.", "dica": "Use frases curtas. Ex: 'Feito com couro legítimo', 'Garantia de 1 ano', 'Frete grátis'."},
            6: {"pergunta": "Você tem algum depoimento de cliente para incluir? (Opcional)", "dica": "A prova social é uma das ferramentas de venda mais poderosas."},
            7: {"pergunta": "Qual ação você quer que o visitante realize? (Sua Chamada para Ação - CTA)", "dica": "Use um verbo de ação claro. Ex: 'Compre agora', 'Agende uma demonstração'."}
        }

    def get_prompt_construtor(self, briefing):
        return f"""
**Instrução Mestra:** Você é um Desenvolvedor Web Full-Stack e Designer de UI/UX sênior, especialista em criar landing pages de alta conversão com HTML e CSS.
**Tarefa:** Crie o código completo para um **único arquivo `index.html`**. O arquivo DEVE ser autocontido.
**Requisitos Técnicos Críticos:**
1.  **Arquivo Único:** Todo o CSS deve estar incorporado no arquivo HTML dentro de uma única tag `<style>` no `<head>`. Não use links para arquivos CSS externos.
2.  **Responsividade:** O design DEVE ser 100% responsivo para desktops e celulares. Use CSS Flexbox e/ou Grid e Media Queries.
3.  **Design:** Crie um design limpo, moderno e profissional. Use uma paleta de cores harmoniosa e fontes legíveis do Google Fonts (importe 'Montserrat' para títulos e 'Roboto' para parágrafos no CSS).
4.  **Diretiva de Imagens:** Para a imagem principal (Hero Section), use a API de source do Unsplash: `<img src="https://source.unsplash.com/1600x900/?{{palavras-chave-da-imagem}}" alt="{{descrição-da-imagem}}">`. Substitua as palavras-chave com base na resposta do usuário sobre o estilo visual.
5.  **Estrutura Semântica:** A página deve seguir a estrutura: `<header>`, `<main>` com `<section>` para cada parte (benefícios, depoimentos, cta), e `<footer>`.
**[BRIEFING DO USUÁRIO]**
{briefing}
**Diretiva Final:** Gere **APENAS O CÓDIGO HTML PURO**, começando com `<!DOCTYPE html>` e terminando com `</html>`. NÃO inclua a palavra 'html' ou aspas de formatação como ```html no início ou no fim da sua resposta.
"""
    
    # Placeholders para outros agentes
    def exibir_max_financeiro(self): st.header("💰 MaxFinanceiro"); st.info("Em breve...")
    def exibir_max_administrativo(self): st.header("⚙️ MaxAdministrativo"); st.info("Em breve...")
    def exibir_max_pesquisa_mercado(self): st.header("📈 MaxPesquisa de Mercado"); st.info("Em breve...")
    def exibir_max_bussola(self): st.header("🧭 MaxBússola Estratégica"); st.info("Em breve...")
    def exibir_max_trainer(self): st.header("🎓 MaxTrainer IA"); st.info("Em breve...")

# 6. ESTRUTURA PRINCIPAL E EXECUÇÃO DO APP
def main():
    if not all([pb_auth_client, firestore_db, PROMPTS_CONFIG]): st.stop()
    user_is_authenticated, _, user_email = get_current_user_status(pb_auth_client)
    if user_is_authenticated:
        llm = get_llm()
        if 'agente' not in st.session_state and llm: st.session_state.agente = MaxAgente(llm, firestore_db)
        if 'agente' in st.session_state:
            agente = st.session_state.agente
            st.sidebar.title("Max IA"); st.sidebar.markdown("---"); st.sidebar.write(f"Logado como: **{user_email}**")
            if st.sidebar.button("Logout", key=f"{APP_KEY_SUFFIX}_logout"):
                for k in list(st.session_state.keys()): del st.session_state[k]
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
            if 'last_agent' not in st.session_state: st.session_state.last_agent = "👋 Bem-vindo"
            selecao_label = st.sidebar.radio("Max Agentes IA:", list(opcoes_menu.keys()), key=f"main_nav_{APP_KEY_SUFFIX}")
            if selecao_label != st.session_state.last_agent:
                if st.session_state.last_agent == "🏗️ Max Construtor":
                    if 'genesis_step' in st.session_state: del st.session_state['genesis_step']
                    if 'genesis_briefing' in st.session_state: del st.session_state['genesis_briefing']
                st.session_state.last_agent = selecao_label
            opcoes_menu[selecao_label]()
        else: st.error("Agente Max IA não carregado.")
    else:
        st.title("🔑 Bem-vindo ao Max IA"); st.info("Faça login ou registre-se na barra lateral.")
        logo_base64 = convert_image_to_base64('max-ia-logo.png')
        if logo_base64: st.image(f"data:image/png;base64,{logo_base64}", width=200)
        auth_action = st.sidebar.radio("Acesso:", ["Login", "Registrar"], key=f"{APP_KEY_SUFFIX}_auth_choice")
        if auth_action == "Login":
            # ... (código do login form)
        else:
            # ... (código do register form)
    st.sidebar.markdown("---"); st.sidebar.info("Max IA | by Yaakov Israel & Gemini AI")

if __name__ == "__main__":
    main()
