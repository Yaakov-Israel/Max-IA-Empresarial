# ==============================================================================
# streamlit_app.py (VERSÃO FÊNIX v2.2 - BASE DE GRIFE)
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
APP_KEY_SUFFIX = "maxia_app_v5.2_brand_base"
USER_COLLECTION = "users"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
PROMPTS_CONFIG = carregar_prompts_config()

# 3. FUNÇÕES AUXILIARES GLOBAIS
# ... (código das funções auxiliares, sem alterações)

# 4. INICIALIZAÇÃO DE SERVIÇOS
# ... (código de inicialização, sem alterações)

# 5. CLASSE PRINCIPAL DO AGENTE
class MaxAgente:
    def __init__(self, llm_instance, db_firestore_instance):
        self.llm = llm_instance; self.db = db_firestore_instance

    # ... (métodos exibir_painel_boas_vindas e exibir_max_marketing_total sem alterações)

    # <<< MÉTODO ATUALIZADO E MELHORADO >>>
    def exibir_max_construtor(self):
        st.header("🏗️ Max Construtor de Landing Pages"); st.caption("Gere a base da sua página e depois a refine no Ateliê.")
        st.markdown("---")
        
        # ... (código de gerenciamento de estado, sem alterações)

        if st.session_state.refinement_mode:
            # ... (código do Ateliê, sem alterações por enquanto)

        elif st.session_state.genesis_html_code:
            # ... (código de exibição da página gerada, sem alterações)
        
        elif st.session_state.genesis_step > len(self.get_perguntas_genesis()):
            st.success("✅ Entrevista Concluída! Revise o briefing abaixo.")
            # ... (código de exibição do resumo do briefing)
            briefing_formatado = ""
            for p, r in st.session_state.genesis_briefing.items():
                briefing_formatado += f"- {p}: {r}\n"
            
            # ... (botões de corrigir e gerar)
            if st.button("🏗️ Gerar Esboço da Página", type="primary", use_container_width=True):
                with st.spinner("🚀 Max Construtor está desenhando uma base de grife..."):
                    # AQUI USAMOS O NOVO PROMPT MELHORADO
                    prompt_construtor = self.get_prompt_construtor(briefing_formatado)
                    try:
                        if self.llm:
                            resposta_ia = self.llm.invoke(prompt_construtor).content
                            html_limpo = resposta_ia.strip().removeprefix("```html").removesuffix("```").strip()
                            st.session_state.genesis_html_code = html_limpo
                            st.rerun()
                        # ... (resto do try/except)
                    except Exception as e: st.error(f"Erro ao contatar a IA: {e}")
        else:
            # Lógica da entrevista, agora com 8 perguntas
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
                            st.session_state.genesis_briefing[p_info["pergunta"]] = resposta; st.session_state.genesis_step -= 1; st.rerun()
                    with col_nav2:
                        if st.form_submit_button("Próxima Pergunta ➡️", use_container_width=True, type="primary"):
                            st.session_state.genesis_briefing[p_info["pergunta"]] = resposta; st.session_state.genesis_step += 1; st.rerun()

    # <<< MÉTODO ATUALIZADO COM AS PERGUNTAS DE BRANDING >>>
    def get_perguntas_genesis(self):
        return {
            1: {"pergunta": "Quais são as 2 ou 3 cores principais da sua marca? (Ex: Azul escuro, branco, dourado)", "dica": "Estas cores serão usadas como base para o design da sua página.", "titulo": "Identidade Visual: Cores", "emoji": "🎨"},
            2: {"pergunta": "Qual o estilo das fontes que você prefere?", "dica": "Isto definirá a personalidade da sua página. Ex: 'Modernas e limpas', 'Elegantes e clássicas', ou 'Ousadas e criativas'.", "titulo": "Identidade Visual: Fontes", "emoji": "✒️"},
            3: {"pergunta": "Qual o nome do seu produto, serviço ou empresa?", "dica": "Seja claro e direto.", "titulo": "Conteúdo: Nome", "emoji": "🏷️"},
            4: {"pergunta": "Qual é a sua grande promessa ou headline principal?", "dica": "Foque na transformação que você gera. Ex: 'Conforto e elegância a cada passo'.", "titulo": "Conteúdo: Headline", "emoji": "💥"},
            5: {"pergunta": "Para quem é esta solução? Descreva seu cliente ideal.", "dica": "'Mulheres de 30-50 anos...' é melhor que 'Pessoas'.", "titulo": "Conteúdo: Público", "emoji": "👥"},
            6: {"pergunta": "Liste 3 características ou benefícios importantes.", "dica": "Use frases curtas e diretas. Ex: 'Feito com couro legítimo', 'Garantia de 1 ano'.", "titulo": "Conteúdo: Benefícios", "emoji": "✅"},
            7: {"pergunta": "Você tem algum depoimento de cliente para incluir? (Nome e texto)", "dica": "A prova social é uma das ferramentas de venda mais poderosas.", "titulo": "Conteúdo: Depoimentos", "emoji": "💬"},
            8: {"pergunta": "Qual ação você quer que o visitante realize? (Sua Chamada para Ação - CTA)", "dica": "Use um verbo de ação claro. Ex: 'Compre agora'.", "titulo": "Conteúdo: CTA", "emoji": "🎯"}
        }

    # <<< MÉTODO ATUALIZADO COM O PROMPT DE 3 ATOS E BRANDING >>>
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
5.  **Placeholders de Imagem:** Use comentários HTML claros: ``, ``.

**[BRIEFING DO USUÁRIO]**
{briefing}
**Diretiva Final:** Gere **APENAS O CÓDIGO HTML PURO**, começando com `<!DOCTYPE html>` e terminando com `</html>`. NÃO inclua ```html.
"""

    def get_prompt_refinamento(self, html_base, logo_b64, main_image_b64):
        # ... (código do prompt de refinamento, sem alterações)
    
    # ... (placeholders dos outros agentes, sem alterações)

# 6. ESTRUTURA PRINCIPAL E EXECUÇÃO DO APP
# ... (função main(), sem alterações)
