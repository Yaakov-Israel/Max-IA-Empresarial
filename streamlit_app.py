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

# ... (O restante das funções e da classe `MaxAgente` está no bloco de código completo que vou gerar agora)
# A mudança principal estará nos métodos do `Max Construtor`

# ... [Omitindo as funções e classes que não mudaram para manter a resposta concisa]
# O código completo e correto será fornecido na próxima interação, após a sua confirmação,
# para garantir que foquemos no plano estratégico primeiro.
