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
# 5. CLASSE PRINCIPAL DO AGENTE
# ==============================================================================
class MaxAgente:
    def __init__(self, llm_instance, db_firestore_instance):
        self.llm = llm_instance
        self.db = db_firestore_instance
# DENTRO da "class MaxAgente:", cole todos os métodos abaixo:
    
    def exibir_painel_boas_vindas(self):
        st.markdown("<div style='text-align: center;'><h1>👋 Bem-vindo ao Max IA!</h1></div>", unsafe_allow_html=True)
        logo_base64 = convert_image_to_base64('max-ia-logo.png')
        if logo_base64:
            st.markdown(f"<div style='text-align: center;'><img src='data:image/png;base64,{logo_base64}' width='200'></div>", unsafe_allow_html=True)
        st.markdown("<div style='text-align: center;'><p style='font-size: 1.2em;'>Olá! Eu sou o <strong>Max</strong>, seu assistente de IA para impulsionar o sucesso da sua empresa.</p></div>", unsafe_allow_html=True)

    # DENTRO DA CLASSE MaxAgente, SUBSTITUA ESTE MÉTODO:
    def exibir_max_marketing_total(self):
        st.header("🚀 MaxMarketing Total")
        st.caption("Seu copiloto para criar posts, campanhas completas e muito mais!")
        st.markdown("---")

        session_key_post = f"mkt_post_{APP_KEY_SUFFIX}"
        if session_key_post not in st.session_state: st.session_state[session_key_post] = None
            
        session_key_campaign = f"mkt_campaign_{APP_KEY_SUFFIX}"
        if session_key_campaign not in st.session_state: st.session_state[session_key_campaign] = None

        opcoes_marketing = ["Criar Post", "Criar campanha completa"]
        acao_selecionada = st.radio("Qual ferramenta do MaxMarketing vamos usar hoje?", opcoes_marketing, key=f"mkt_radio_{APP_KEY_SUFFIX}")

        ## --- INÍCIO DO SUB-MÓDULO: CRIAR POST --- ##
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
                                # ... (Lógica de prompt dinâmico que já funciona)
                                pass
        ## --- FIM DO SUB-MÓDULO: CRIAR POST --- ##
        
        ## --- INÍCIO DO SUB-MÓDULO: CRIAR CAMPANHA COMPLETA --- ##
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
        ## --- FIM DO SUB-MÓDULO: CRIAR CAMPANHA COMPLETA --- ##
    
    ## --- INÍCIO DO SUB-MÓDULO 5.1: Max Construtor --- ##

    def exibir_max_construtor(self):
        st.header("🏗️ Max Vitrine Digital"); st.caption("Crie uma página de vendas para seus produtos ou serviços.")
        st.markdown("---")
        
        # Gerenciamento de Estado
        if 'genesis_step' not in st.session_state: st.session_state.genesis_step = 0
        if 'genesis_briefing' not in st.session_state: st.session_state.genesis_briefing = {}
        if 'genesis_html_code' not in st.session_state: st.session_state.genesis_html_code = None
        if 'refinement_mode' not in st.session_state: st.session_state.refinement_mode = False

        # MODO ATELIÊ DE REFINAMENTO
        if st.session_state.refinement_mode:
            st.subheader("🎨 Ateliê de Refinamento")
            st.info("Faça o upload dos seus arquivos para personalizar a página. A mágica acontecerá em seguida!")
            
            with st.form(key="refinement_form"):
                logo_file = st.file_uploader("1. Logo da sua empresa (PNG com fundo transparente recomendado)", type=['png', 'jpg', 'jpeg'])
                main_image_file = st.file_uploader("2. Imagem principal (para a primeira seção)", type=['png', 'jpg', 'jpeg'])
                
                submitted = st.form_submit_button("✨ Aplicar Personalizações", type="primary", use_container_width=True)
                
                if submitted:
                    if not logo_file and not main_image_file:
                        st.warning("Por favor, suba pelo menos um arquivo para personalizar.")
                    else:
                        with st.spinner("🔧 Max está no Ateliê, aplicando seus toques finais..."):
                            logo_b64, main_image_b64 = None, None
                            if logo_file:
                                logo_bytes = logo_file.getvalue()
                                logo_b64 = base64.b64encode(logo_bytes).decode()
                            if main_image_file:
                                main_image_bytes = main_image_file.getvalue()
                                main_image_b64 = base64.b64encode(main_image_bytes).decode()
                            
                            html_base = st.session_state.genesis_html_code
                            prompt_refinamento = self.get_prompt_refinamento(html_base, logo_b64, main_image_b64)
                            
                            try:
                                if self.llm and prompt_refinamento:
                                    resposta_ia = self.llm.invoke(prompt_refinamento).content
                                    html_final = resposta_ia.strip().removeprefix("```html").removesuffix("```").strip()
                                    st.session_state.genesis_html_code = html_final
                                    st.session_state.refinement_mode = False
                                    st.rerun()
                                else:
                                    st.error("Nenhuma personalização a ser feita ou LLM indisponível.")
                            except Exception as e:
                                st.error(f"Ocorreu um erro durante o refinamento: {e}")

            if st.button("⬅️ Voltar para o Esboço"):
                st.session_state.refinement_mode = False
                st.rerun()

        # MODO DE EXIBIÇÃO DA PÁGINA GERADA
        elif st.session_state.genesis_html_code:
            st.success("✅ Sua Página de Venda foi gerada!"); st.markdown("---")
            
            st.subheader("🎨 Próximos Passos")
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("🎨 Personalizar com Imagens", use_container_width=True, type="primary"):
                    st.session_state.refinement_mode = True
                    st.rerun()
            with col2:
                st.download_button(label="📥 Baixar Código HTML", data=st.session_state.genesis_html_code, file_name="pagina_de_venda.html", mime="text/html", use_container_width=True)
            with col3:
                if st.button("✨ Começar do Zero", use_container_width=True):
                    keys_to_reset = ['genesis_step', 'genesis_briefing', 'genesis_html_code', 'refinement_mode']
                    for key in keys_to_reset:
                        if key in st.session_state: del st.session_state[key]
                    st.rerun()

            st.subheader("👀 Pré-visualização")
            st.components.v1.html(st.session_state.genesis_html_code, height=600, scrolling=True)
            with st.expander("🚀 Sua página está pronta! E agora? (Dicas de Hospedagem)"):
                st.markdown("""
                🎓 **MaxTrainer diz:** Publicar sua página é mais fácil do que parece! Com o arquivo `index.html` em mãos, você pode colocá-la no ar em minutos.
                1.  **Netlify Drop:** Ideal para a maneira mais rápida. Basta arrastar e soltar seu arquivo. Link: [https://app.netlify.com/drop](https://app.netlify.com/drop)
                2.  **Vercel:** Muito poderosa e com ótima performance. Link: [https://vercel.com](https://vercel.com)
                """)

        # MODO DE RESUMO DA ENTREVISTA
        elif st.session_state.genesis_step > len(self.get_perguntas_vitrine()):
            st.success("✅ Entrevista Concluída! Revise o briefing abaixo.")
            st.markdown("---"); st.subheader("Resumo do Briefing:")
            briefing_formatado = ""
            for p_info in self.get_perguntas_vitrine().values():
                pergunta = p_info["pergunta"]
                resposta = st.session_state.genesis_briefing.get(pergunta, "Não preenchido")
                st.markdown(f"**{p_info['emoji']} {p_info['titulo']}**"); st.markdown(f"> {resposta}")
                briefing_formatado += f"- {p_info['titulo']}: {resposta}\n"
            st.markdown("---")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("⬅️ Corrigir Respostas", use_container_width=True):
                    st.session_state.genesis_step = 1; st.rerun()
            with col2:
                if st.button("🏗️ Gerar Página de Venda", type="primary", use_container_width=True):
                    with st.spinner("🚀 Max Construtor está desenhando uma base de grife..."):
                        prompt_construtor = self.get_prompt_vitrine(briefing_formatado)
                        try:
                            if self.llm:
                                resposta_ia = self.llm.invoke(prompt_construtor).content
                                html_limpo = resposta_ia.strip().removeprefix("```html").removesuffix("```").strip()
                                st.session_state.genesis_html_code = html_limpo
                                st.rerun()
                            else: st.error("LLM não disponível.")
                        except Exception as e: st.error(f"Erro ao contatar a IA: {e}")
        
        # MODO DE ENTREVISTA
        else:
            perguntas = self.get_perguntas_vitrine()
            step = st.session_state.genesis_step
            if step == 0:
                st.info("Eu sou o Max Construtor. Juntos, vamos criar uma Página de Venda de alta performance respondendo a uma breve entrevista.")
                if st.button("Vamos Começar!", type="primary"):
                    st.session_state.genesis_step = 1; st.rerun()
            else:
                p_info = perguntas[step]
                st.progress(step / len(perguntas))
                st.subheader(f"{p_info['emoji']} {p_info['titulo']} ({step}/{len(perguntas)})")
                with st.expander("🎓 Dica do MaxTrainer"): st.write(p_info["dica"])
                with st.form(key=f"genesis_form_{step}"):
                    default_value = st.session_state.genesis_briefing.get(p_info["pergunta"], "")
                    resposta = st.text_area(p_info["pergunta"], value=default_value, key=f"genesis_input_{step}", height=125)
                    col_nav1, col_nav2 = st.columns(2)
                    with col_nav1:
                        if st.form_submit_button("⬅️ Pergunta Anterior", use_container_width=True, disabled=(step == 1)):
                            st.session_state.genesis_briefing[p_info["pergunta"]] = resposta
                            st.session_state.genesis_step -= 1; st.rerun()
                    with col_nav2:
                        if st.form_submit_button("Próxima Pergunta ➡️", use_container_width=True, type="primary"):
                            st.session_state.genesis_briefing[p_info["pergunta"]] = resposta
                            st.session_state.genesis_step += 1; st.rerun()

    def get_perguntas_vitrine(self):
        return {
            1: {"pergunta": "Quais são as 2 ou 3 cores principais da sua marca? (Ex: Azul escuro, branco, dourado)", "dica": "Estas cores serão usadas como base para o design da sua página.", "titulo": "Identidade Visual: Cores", "emoji": "🎨"},
            2: {"pergunta": "Qual o estilo das fontes que você prefere?", "dica": "Isto definirá a personalidade da sua página. Ex: 'Modernas e limpas', 'Elegantes e clássicas', ou 'Ousadas e criativas'.", "titulo": "Identidade Visual: Fontes", "emoji": "✒️"},
            3: {"pergunta": "Qual o nome da sua empresa ou produto principal?", "dica": "Seja claro e direto.", "titulo": "Conteúdo: Nome Principal", "emoji": "🏷️"},
            4: {"pergunta": "Qual é a sua grande promessa ou headline principal?", "dica": "Foque na transformação que você gera. Ex: 'Conforto e elegância a cada passo'.", "titulo": "Conteúdo: Headline", "emoji": "💥"},
            5: {"pergunta": "Liste de 3 a 6 produtos ou serviços que você quer exibir, com uma breve descrição para cada um.", "dica": "Seja claro e direto nos benefícios. Ex: 'Sapato Social Confort - Couro legítimo, palmilha anatômica.'", "titulo": "Conteúdo: Produtos/Serviços", "emoji": "🛍️"},
            6: {"pergunta": "Você tem algum depoimento de cliente para incluir? (Nome e texto)", "dica": "A prova social é uma das ferramentas de venda mais poderosas.", "titulo": "Conteúdo: Depoimentos", "emoji": "💬"},
            7: {"pergunta": "Qual ação final você quer que o visitante realize? (Sua Chamada para Ação - CTA)", "dica": "Use um verbo de ação claro. Ex: 'Compre agora pelo WhatsApp', 'Veja nosso catálogo completo'.", "titulo": "Conteúdo: CTA Final", "emoji": "🎯"}
        }

    def get_prompt_construtor(self, briefing):
        return f"""
**Instrução Mestra:** Você é um Desenvolvedor Web Full-Stack e Designer de UI/UX sênior, especialista em criar PÁGINAS DE VENDA (Vitrines Digitais) de alta qualidade com HTML e CSS.
**Tarefa:** Crie o código completo para um **único arquivo `index.html`**. O arquivo DEVE ser autocontido e usar as informações de branding e conteúdo do briefing para criar uma vitrine de produtos/serviços.
**Requisitos Críticos:**
1.  **Autocontido:** Todo o CSS deve estar dentro de uma tag `<style>` no `<head>`.
2.  **Responsivo:** O design DEVE ser 100% responsivo para desktops e celulares.
3.  **Diretiva de Estilo:** Use as informações de branding do briefing. A cor primária deve ser usada nos botões e títulos principais. As fontes devem ser importadas do Google Fonts e escolhidas com base no estilo pedido pelo usuário (se pediu 'Modernas', use 'Montserrat' e 'Lato'; se pediu 'Elegantes', use 'Playfair Display' e 'Roboto'; se pediu 'Ousadas', use 'Poppins' e 'Open Sans').
4.  **Diretiva de Estrutura (3 Atos):**
    * **Header:** Crie um cabeçalho simples com um ``.
    * **Ato 1 (Hero Section):** Crie uma seção de topo impactante com a headline principal (h1) e um placeholder para imagem: ``.
    * **Ato 2 (Vitrine de Produtos):** Crie uma seção com um título (h2) e use CSS Grid para exibir os produtos/serviços listados no briefing em 'cards'. Cada card deve ter o nome do produto (h3) e sua descrição (p). Não adicione placeholders de imagem para cada produto ainda.
    * **Ato 3 (Prova Social e CTA):** Crie uma seção para os depoimentos (se houver) e uma seção final de Chamada para Ação com um botão bem visível.
    * **Footer:** Um rodapé simples.
**[BRIEFING DO USUÁRIO]**
{briefing}
**Diretiva Final:** Gere **APENAS O CÓDIGO HTML PURO**, começando com `<!DOCTYPE html>` e terminando com `</html>`. NÃO inclua ```html.
"""

    def get_prompt_refinamento(self, html_base, logo_b64, main_image_b64):
        instrucoes = []
        if logo_b64:
            instrucoes.append(f"1. Encontre o comentário `` e substitua-o por esta tag de imagem: `<img src='data:image/png;base64,{logo_b64}' alt='Logo da Empresa' style='max-height: 70px;'>`")
        if main_image_b64:
            instrucoes.append(f"2. Encontre o comentário `` e substitua-o por esta tag de imagem: `<img src='data:image/jpeg;base64,{main_image_b64}' alt='Imagem Principal do Produto' style='width: 100%; height: auto; border-radius: 8px;'>`")
        
        if not instrucoes:
            return None

        instrucao_str = "\n".join(instrucoes)

        # AQUI ESTÁ A MUDANÇA: usando parênteses em vez de aspas triplas
        return (
            "**Instrução Mestra:** Você é um desenvolvedor web sênior que refatora um código HTML existente.\n"
            "**Tarefa:** Receba um código HTML base e um conjunto de instruções. Aplique as instruções para substituir os placeholders de comentário pelas tags de imagem fornecidas.\n\n"
            "**CÓDIGO HTML BASE:**\n"
            "```html\n"
            f"{html_base}\n"
            "```\n\n"
            "**INSTRUÇÕES DE MODIFICAÇÃO:**\n"
            f"{instrucao_str}\n\n"
            "**Diretiva Final:** Retorne **APENAS O NOVO CÓDIGO HTML COMPLETO**, começando com `<!DOCTYPE html>` e terminando com `</html>`. NÃO inclua explicações ou aspas de formatação."
        )

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
