# ==============================================================================
# streamlit_app.py (VERSÃO FÊNIX v2.1 - BASE SÓLIDA PARA O ATELIÊ)
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
APP_KEY_SUFFIX = "maxia_app_v5.1_solid_base"
USER_COLLECTION = "users"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
PROMPTS_CONFIG = carregar_prompts_config()

# ==============================================================================
# 5. CLASSE PRINCIPAL DO AGENTE (VERSÃO COM ATELIÊ DO CONSTRUTOR v2.1 - SPRINT 1)
# ==============================================================================
class MaxAgente:
    def __init__(self, llm_instance, db_firestore_instance):
        self.llm = llm_instance; self.db = db_firestore_instance

    def exibir_painel_boas_vindas(self):
        st.markdown("<div style='text-align: center;'><h1>👋 Bem-vindo ao Max IA!</h1></div>", unsafe_allow_html=True)
        logo_base64 = convert_image_to_base64('max-ia-logo.png')
        if logo_base64: st.markdown(f"<div style='text-align: center;'><img src='data:image/png;base64,{logo_base64}' width='200'></div>", unsafe_allow_html=True)
        st.markdown("<div style='text-align: center;'><p style='font-size: 1.2em;'>Olá! Eu sou o <strong>Max</strong>, seu assistente de IA para impulsionar o sucesso da sua empresa.</p></div>", unsafe_allow_html=True)

    def exibir_max_marketing_total(self):
        # Este método está completo e funcional. Nenhuma alteração aqui.
        st.header("🚀 MaxMarketing Total"); st.caption("Seu copiloto para criar posts, campanhas completas e muito mais!")
        st.markdown("---")
        session_key_post = f"mkt_post_{APP_KEY_SUFFIX}";
        if session_key_post not in st.session_state: st.session_state[session_key_post] = None
        session_key_campaign = f"mkt_campaign_{APP_KEY_SUFFIX}"
        if session_key_campaign not in st.session_state: st.session_state[session_key_campaign] = None
        opcoes_marketing = ["Criar Post", "Criar campanha completa"]
        acao_selecionada = st.radio("Qual ferramenta do MaxMarketing vamos usar hoje?", opcoes_marketing, key=f"mkt_radio_{APP_KEY_SUFFIX}")
        if acao_selecionada == "Criar Post":
            st.session_state[session_key_campaign] = None
            if st.session_state[session_key_post]:
                st.subheader("🎉 Conteúdo Gerado pelo Max IA!"); st.markdown(st.session_state[session_key_post]); st.markdown("---")
                st.subheader("📥 Baixar Conteúdo")
                col1, col2 = st.columns([0.7, 0.3])
                with col1: formato = st.selectbox("Formato:", ("txt", "docx", "pdf"), key=f"dl_fmt_post_{APP_KEY_SUFFIX}")
                with col2:
                    st.write(""); st.write("")
                    try:
                        arquivo_bytes = gerar_arquivo_download(st.session_state[session_key_post], formato)
                        if arquivo_bytes: st.download_button(f"Baixar .{formato}", arquivo_bytes, f"post_max_ia.{formato}", use_container_width=True)
                    except Exception as e: st.error(f"Erro no download: {e}")
                st.markdown("---")
                if st.button("✨ Criar Outro Conteúdo"): st.session_state[session_key_post] = None; st.rerun()
            else:
                st.subheader("📝 Briefing do Conteúdo")
                with st.form(key=f"mkt_form_post_{APP_KEY_SUFFIX}"):
                    formatos_disponiveis = ["Instagram Post (Feed)", "Instagram Stories", "Instagram Reels (Roteiro)","Facebook Post", "Facebook Stories","Mensagem para WhatsApp", "E-mail Marketing", "Google ADS (Texto)","Roteiro de Vídeo YouTube", "Roteiro para TikTok", "Post para X (Twitter)","Anúncio para OLX / Mercado Livre", "Descrição de Produto para Shopify / E-commerce"]
                    formato_selecionado = st.selectbox("1. Primeiro, escolha o formato do conteúdo:", formatos_disponiveis)
                    objetivo = st.text_area("2. Qual o objetivo deste conteúdo?")
                    publico = st.text_input("3. Quem você quer alcançar?")
                    produto_servico = st.text_area("4. Qual produto ou serviço principal está promovendo?")
                    info_adicional = st.text_area("5. Alguma informação adicional, oferta ou CTA (Chamada para Ação)?")
                    if st.form_submit_button("💡 Gerar Conteúdo com Max IA!"):
                        if not objetivo: st.warning("O objetivo é essencial.")
                        else:
                            with st.spinner(f"🤖 Max IA está pensando como um especialista em {formato_selecionado}..."):
                                instrucao_base = f"**Contexto do Negócio:**\n- **Objetivo:** {objetivo}\n- **Público-alvo:** {publico}\n- **Produto/Serviço:** {produto_servico}\n- **Informações Adicionais/CTA:** {info_adicional}"
                                if "OLX" in formato_selecionado or "Mercado Livre" in formato_selecionado:
                                    especialista = "um vendedor experiente de marketplaces como OLX e Mercado Livre."
                                    tarefa = "Crie um anúncio otimizado. Gere um Título chamativo (máx 60 caracteres) e uma Descrição detalhada e persuasiva, incluindo benefícios, especificações técnicas (se aplicável) e condições. Use parágrafos curtos."
                                elif "Shopify" in formato_selecionado or "E-commerce" in formato_selecionado:
                                    especialista = "um especialista em copywriting para e-commerce."
                                    tarefa = "Crie uma descrição de produto completa e otimizada para SEO. Gere um Título de Produto claro e descritivo, uma Descrição Persuasiva focada nos benefícios e na transformação que o produto causa, e uma lista de 3 a 5 bullet points com as principais características técnicas."
                                else:
                                    # Lógica para outras plataformas
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
                st.subheader("🎉 Plano de Campanha Gerado pelo Max IA!"); resposta_completa = st.session_state[session_key_campaign]
                st.markdown("---")
                with st.expander("
