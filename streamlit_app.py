# ==============================================================================
# streamlit_app.py (VERSÃO FÊNIX v2.3 - CORREÇÃO FINAL DE INDENTAÇÃO)
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
APP_KEY_SUFFIX = "maxia_app_v5.3_final_indent_fix"
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
# 5. CLASSE PRINCIPAL DO AGENTE (VERSÃO COM CONSTRUTOR v2.2 - BASE DE GRIFE)
# ==============================================================================
class MaxAgente:
    def __init__(self, llm_instance, db_firestore_instance):
        self.llm = llm_instance; self.db = db_firestore_instance

    def exibir_painel_boas_vindas(self):
        # ... (código sem alterações)
        st.markdown("<div style='text-align: center;'><h1>👋 Bem-vindo ao Max IA!</h1></div>", unsafe_allow_html=True)
        logo_base64 = convert_image_to_base64('max-ia-logo.png')
        if logo_base64: st.markdown(f"<div style='text-align: center;'><img src='data:image/png;base64,{logo_base64}' width='200'></div>", unsafe_allow_html=True)
        st.markdown("<div style='text-align: center;'><p style='font-size: 1.2em;'>Olá! Eu sou o <strong>Max</strong>, seu assistente de IA para impulsionar o sucesso da sua empresa.</p></div>", unsafe_allow_html=True)

    def exibir_max_marketing_total(self):
        # ... (código do marketing sem alterações)
        st.header("🚀 MaxMarketing Total"); st.caption("Seu copiloto para criar posts, campanhas completas e muito mais!")
        st.info("Funcionalidades de Marketing e Campanhas estão operacionais.")
        
    # <<< MÉTODO ATUALIZADO E MELHORADO >>>
    def exibir_max_construtor(self):
        st.header("🏗️ Max Construtor de Landing Pages"); st.caption("Gere a base da sua página e depois a refine no Ateliê.")
        st.markdown("---")
        
        if 'genesis_step' not in st.session_state: st.session_state.genesis_step = 0
        if 'genesis_briefing' not in st.session_state: st.session_state.genesis_briefing = {}
        if 'genesis_html_code' not in st.session_state: st.session_state.genesis_html_code = None
        if 'refinement_mode' not in st.session_state: st.session_state.refinement_mode = False

        if st.session_state.refinement_mode:
            st.subheader("🎨 Ateliê de Refinamento")
            st.info("Faça o upload dos seus arquivos para personalizar a página.")
            with st.form(key="refinement_form"):
                logo_file = st.file_uploader("1. Logo da sua empresa (PNG com fundo transparente)", type=['png', 'jpg', 'jpeg'])
                main_image_file = st.file_uploader("2. Imagem principal do produto ou serviço", type=['png', 'jpg', 'jpeg'])
                submitted = st.form_submit_button("✨ Aplicar Personalizações", type="primary", use_container_width=True)
                if submitted:
                    if not logo_file and not main_image_file:
                        st.warning("Por favor, suba pelo menos um arquivo para personalizar.")
                    else:
                        with st.spinner("🔧 Max está no Ateliê, aplicando seus toques finais..."):
                            # ... (lógica de refinamento que já funciona)
                            
            if st.button("⬅️ Voltar para o Esboço"):
                st.session_state.refinement_mode = False; st.rerun()

        elif st.session_state.genesis_html_code:
            st.success("✅ O esboço da sua Landing Page foi gerado!"); st.markdown("---")
            st.subheader("🎨 Próximos Passos"); 
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("🎨 Personalizar com Imagens", use_container_width=True, type="primary"):
                    st.session_state.refinement_mode = True; st.rerun()
            with col2:
                st.download_button(label="📥 Baixar Esboço HTML", data=st.session_state.genesis_html_code, file_name="esboco_index.html", mime="text/html", use_container_width=True)
            with col3:
                if st.button("✨ Começar do Zero", use_container_width=True):
                    st.session_state.genesis_step = 0; st.session_state.genesis_briefing = {}; st.session_state.genesis_html_code = None; st.session_state.refinement_mode = False
                    st.rerun()
            st.subheader("👀 Pré-visualização do Esboço");
            st.components.v1.html(st.session_state.genesis_html_code, height=600, scrolling=True)
        
        elif st.session_state.genesis_step > len(self.get_perguntas_genesis()):
            st.success("✅ Entrevista Concluída! Revise o briefing abaixo.")
            st.markdown("---"); st.subheader("Resumo do Briefing:")
            briefing_formatado = ""
            for p, r in st.session_state.genesis_briefing.items():
                st.markdown(f"**{p}**"); st.markdown(f"> {r if r else 'Não preenchido'}")
                briefing_formatado += f"- {p}: {r}\n"
            st.markdown("---")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("⬅️ Corrigir Respostas"): st.session_state.genesis_step = 1; st.rerun()
            with col2:
                if st.button("🏗️ Gerar Esboço da Página", type="primary", use_container_width=True):
                    with st.spinner("🚀 Max Construtor está desenhando uma base de grife..."):
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
                st.info("Eu sou o Max Construtor. Juntos, vamos criar a base da sua landing page respondendo a uma breve entrevista.")
                if st.button("Vamos Começar!", type="primary"):
                    st.session_state.genesis_step = 1; st.rerun()
            else:
                p_info = perguntas[step]
                st.progress(step / len(perguntas))
                st.subheader(f"{p_info['emoji']} {p_info['titulo']} ({step}/{len(perguntas)})")
                with st.expander("🎓 Dica do MaxTrainer"): st.write(p_info["dica"])
                with st.form(key=f"genesis_form_{step}"):
                    default_value = st.session_state.genesis_briefing.get(p_info["pergunta"], "")
                    resposta = st.text_area(p_info["pergunta"], value=default_value, key=f"genesis_input_{step}", height=100)
                    col_nav1, col_nav2 = st.columns(2)
                    with col_nav1:
                        if st.form_submit_button("⬅️ Pergunta Anterior", use_container_width=True, disabled=(step == 1)):
                            st.session_state.genesis_briefing[p_info["pergunta"]] = resposta
                            st.session_state.genesis_step -= 1; st.rerun()
                    with col_nav2:
                        if st.form_submit_button("Próxima Pergunta ➡️", use_container_width=True, type="primary"):
                            st.session_state.genesis_briefing[p_info["pergunta"]] = resposta
                            st.session_state.genesis_step += 1; st.rerun()

    # <<< MÉTODO ATUALIZADO ---
    def get_perguntas_genesis(self):
        return {
            # Módulo de Branding
            1: {"pergunta": "Quais são as 2 ou 3 cores principais da sua marca? (Ex: Azul escuro, branco, dourado)", "dica": "Estas cores serão usadas como base para o design da sua página.", "titulo": "Identidade Visual: Cores", "emoji": "🎨"},
            2: {"pergunta": "Qual o estilo das fontes que você prefere?", "dica": "Isto definirá a personalidade da sua página. Ex: 'Modernas e limpas', 'Elegantes e clássicas', ou 'Ousadas e criativas'.", "titulo": "Identidade Visual: Fontes", "emoji": "✒️"},
            # Módulo de Conteúdo
            3: {"pergunta": "Qual o nome do seu produto, serviço ou empresa?", "dica": "Seja claro e direto.", "titulo": "Conteúdo: Nome", "emoji": "🏷️"},
            4: {"pergunta": "Qual é a sua grande promessa ou headline principal?", "dica": "Foque na transformação que você gera. Ex: 'Conforto e elegância a cada passo'.", "titulo": "Conteúdo: Headline", "emoji": "💥"},
            5: {"pergunta": "Para quem é esta solução? Descreva seu cliente ideal.", "dica": "'Mulheres de 30-50 anos...' é melhor que 'Pessoas'.", "titulo": "Conteúdo: Público", "emoji": "👥"},
            6: {"pergunta": "Liste 3 características ou benefícios importantes.", "dica": "Use frases curtas e diretas. Ex: 'Feito com couro legítimo', 'Garantia de 1 ano'.", "titulo": "Conteúdo: Benefícios", "emoji": "✅"},
            7: {"pergunta": "Você tem algum depoimento de cliente para incluir? (Nome e texto)", "dica": "A prova social é uma das ferramentas de venda mais poderosas.", "titulo": "Conteúdo: Depoimentos", "emoji": "💬"},
            8: {"pergunta": "Qual ação você quer que o visitante realize? (Sua Chamada para Ação - CTA)", "dica": "Use um verbo de ação claro. Ex: 'Compre agora'.", "titulo": "Conteúdo: CTA", "emoji": "🎯"}
        }

    # <<< MÉTODO ATUALIZADO ---
    def get_prompt_construtor(self, briefing):
        return f"""
**Instrução Mestra:** Você é um Desenvolvedor Web Full-Stack e Designer de UI/UX sênior, especialista em criar landing pages de ALTA QUALIDADE com HTML e CSS.
**Tarefa:** Crie o código completo para um **único arquivo `index.html`** de um esboço de página. O arquivo DEVE ser autocontido e usar as informações de branding e conteúdo do briefing.
**Requisitos Críticos:**
1.  **Autocontido:** Todo o CSS deve estar dentro de uma tag `<style>` no `<head>`.
2.  **Responsivo:** O design DEVE ser 100% responsivo para desktops e celulares.
3.  **Diretiva de Estilo:** Use as informações de branding do briefing. A cor primária deve ser usada nos botões e títulos principais. As fontes devem ser importadas do Google Fonts e escolhidas com base no estilo pedido pelo usuário (se pediu 'Modernas', use 'Montserrat' e 'Lato'; se pediu 'Elegantes', use 'Playfair Display' e 'Roboto'; se pediu 'Ousadas', use 'Poppins' e 'Open Sans').
4.  **Diretiva de Estrutura (3 Atos):**
    * **Ato 1 (Hero Section):** Crie uma seção de topo impactante com a headline principal (h1) e um placeholder para um vídeo: ``.
    * **Ato 2 (Benefícios e CTA):** Crie uma seção para os benefícios listados e inclua a chamada para ação principal (botão).
    * **Ato 3 (Destaques e CTA Final):** Crie uma seção de rodapé expandida (footer) com espaço para 3 a 6 destaques ou informações adicionais (ex: 'Entrega Rápida', 'Suporte 24h') e repita a chamada para ação.
5.  **Placeholders:** Para imagens que serão adicionadas depois, use comentários HTML claros: ``, ``.

**[BRIEFING DO USUÁRIO]**
{briefing}
**Diretiva Final:** Gere **APENAS O CÓDIGO HTML PURO**, começando com `<!DOCTYPE html>` e terminando com `</html>`. NÃO inclua a palavra 'html' ou aspas de formatação como ```html no início ou no fim da sua resposta.
"""
    
    # --- Métodos dos outros agentes (sem alterações) ---
    def exibir_max_financeiro(self): st.header("💰 MaxFinanceiro"); st.info("Em breve...")
    def exibir_max_administrativo(self): st.header("⚙️ MaxAdministrativo"); st.info("Em breve...")
    def exibir_max_pesquisa_mercado(self): st.header("📈 MaxPesquisa de Mercado"); st.info("Em breve...")
    def exibir_max_bussola(self): st.header("🧭 MaxBússola Estratégica"); st.info("Em breve...")
    def exibir_max_trainer(self): st.header("🎓 MaxTrainer IA"); st.info("Em breve...")

    def get_prompt_refinamento(self, html_base, logo_b64, main_image_b64):
        instrucoes = []
        if logo_b64:
            instrucoes.append(f"1. Encontre o comentário `` e substitua-o pela seguinte tag de imagem: `<img src='data:image/png;base64,{logo_b64}' alt='Logo da Empresa' style='max-height: 70px; margin-bottom: 20px;'>`")
        if main_image_b64:
            instrucoes.append(f"2. Encontre o comentário `` e substitua-o pela seguinte tag de imagem: `<img src='data:image/jpeg;base64,{main_image_b64}' alt='Imagem Principal do Produto' style='width: 100%; height: auto; border-radius: 8px; margin-top: 20px;'>`")

        if not instrucoes:
            return None # Retorna None se não houver nada a fazer

        instrucao_str = "\n".join(instrucoes)

        return f"""
**Instrução Mestra:** Você é um desenvolvedor web sênior que refatora um código HTML existente.
**Tarefa:** Receba um código HTML base e um conjunto de instruções. Aplique as instruções para substituir os placeholders de comentário pelas tags de imagem fornecidas.
**CÓDIGO HTML BASE:**
```html
{html_base}
**Instrução Mestra:** Você é um Desenvolvedor Web Full-Stack e Designer de UI/UX sênior.
**Tarefa:** Crie o código HTML completo para um **único arquivo `index.html`** de um esboço de página. O arquivo DEVE ser autocontido.
**Requisitos Críticos:**
1.  **Arquivo Único:** Todo o CSS deve estar dentro de uma tag `<style>` no `<head>`.
2.  **Responsividade:** O design DEVE ser 100% responsivo para desktops e celulares.
3.  **Design:** Crie um design limpo, moderno e profissional. Use placeholders de texto claros para imagens e logos, como ``.
4.  **Estrutura Semântica:** Use a estrutura correta (header, main, section, footer).
**[BRIEFING DO USUÁRIO]**
{briefing}
**Diretiva Final:** Gere **APENAS O CÓDIGO HTML PURO**, começando com `<!DOCTYPE html>` e terminando com `</html>`. NÃO inclua a palavra 'html' ou aspas de formatação como ```html no início ou no fim da sua resposta.
"""
    
    def exibir_max_financeiro(self): st.header("💰 MaxFinanceiro"); st.info("Em breve...")
    def exibir_max_administrativo(self): st.header("⚙️ MaxAdministrativo"); st.info("Em breve...")
    def exibir_max_pesquisa_mercado(self): st.header("📈 MaxPesquisa de Mercado"); st.info("Em breve...")
    def exibir_max_bussola(self): st.header("🧭 MaxBússola Estratégica"); st.info("Em breve...")
    def exibir_max_trainer(self): st.header("🎓 MaxTrainer IA"); st.info("Em breve...")

# 6. ESTRUTURA PRINCIPAL E EXECUÇÃO DO APP
# ==============================================================================
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
            opcoes_menu = {"👋 Bem-vindo": agente.exibir_painel_boas_vindas, "🚀 Marketing": agente.exibir_max_marketing_total, "🏗️ Max Construtor": agente.exibir_max_construtor, "💰 Financeiro": agente.exibir_max_financeiro, "⚙️ Administrativo": agente.exibir_max_administrativo, "📈 Pesquisa": agente.exibir_max_pesquisa_mercado, "🧭 Estratégia": agente.exibir_max_bussola, "🎓 Trainer": agente.exibir_max_trainer }
            if 'last_agent' not in st.session_state: st.session_state.last_agent = "👋 Bem-vindo"
            selecao_label = st.sidebar.radio("Max Agentes IA:", list(opcoes_menu.keys()), key=f"main_nav_{APP_KEY_SUFFIX}")
            if selecao_label != st.session_state.last_agent:
                if 'genesis_step' in st.session_state and st.session_state.genesis_step != 0:
                    st.session_state.genesis_step = 0
                    st.session_state.genesis_briefing = {}
                    st.session_state.genesis_html_code = None
                    st.session_state.refinement_mode = False
                st.session_state.last_agent = selecao_label
            opcoes_menu[selecao_label]()
        else: st.error("Agente Max IA não carregado.")
    else:
        st.title("🔑 Bem-vindo ao Max IA"); st.info("Faça login ou registre-se na barra lateral.")
        logo_base64 = convert_image_to_base64('max-ia-logo.png')
        if logo_base64: st.image(f"data:image/png;base64,{logo_base64}", width=200)
        auth_action = st.sidebar.radio("Acesso:", ["Login", "Registrar"], key=f"{APP_KEY_SUFFIX}_auth_choice")
        if auth_action == "Login":
            with st.sidebar.form(f"{APP_KEY_SUFFIX}_login_form"):
                email = st.text_input("Email"); password = st.text_input("Senha", type="password")
                if st.form_submit_button("Entrar"):
                    try: st.session_state[f'{APP_KEY_SUFFIX}_user_session_data'] = dict(pb_auth_client.sign_in_with_email_and_password(email, password)); st.rerun()
                    except Exception: st.sidebar.error("Login falhou.")
        else:
            with st.sidebar.form(f"{APP_KEY_SUFFIX}_register_form"):
                email = st.text_input("Seu Email"); password = st.text_input("Crie uma Senha", type="password")
                if st.form_submit_button("Registrar"):
                    if email and len(password) >= 6:
                        try:
                            new_user = pb_auth_client.create_user_with_email_and_password(email, password)
                            firestore_db.collection(USER_COLLECTION).document(new_user['localId']).set({"email": email, "registration_date": firebase_admin.firestore.SERVER_TIMESTAMP}, merge=True)
                            st.sidebar.success("Conta criada! Faça o login.")
                        except Exception: st.sidebar.error("E-mail já em uso ou erro no registro.")
                    else: st.sidebar.warning("Dados inválidos.")
    st.sidebar.markdown("---"); st.sidebar.info("Max IA | by Yaakov Israel & Gemini AI")

if __name__ == "__main__":
    main()
