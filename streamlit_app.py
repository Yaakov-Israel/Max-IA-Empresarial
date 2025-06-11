# ==============================================================================
# 1. IMPORTAÇÕES E CONFIGURAÇÃO INICIAL DA PÁGINA
# ==============================================================================
import streamlit as st
import os
import io
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
import plotly.graph_objects as go

# --- INÍCIO DA CONFIGURAÇÃO DE CAMINHOS E DIRETÓRIOS ---
# Padroniza o diretório de assets para robustez na implantação.
# CRIE UMA PASTA CHAMADA "assets" NA RAIZ DO SEU PROJETO E COLOQUE SUAS IMAGENS E FONTES LÁ.
ASSETS_DIR = "assets"

def get_asset_path(asset_name):
    """Constrói o caminho para um asset dentro da pasta 'assets' de forma segura."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), ASSETS_DIR, asset_name)

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
APP_KEY_SUFFIX = "maxia_app_v11.0_full_integration"
USER_COLLECTION = "users"
COMPANY_COLLECTION = "companies"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
SALES_PAGE_URL = "https://sua-pagina-de-vendas.com.br" # <-- IMPORTANTE: Substitua por sua URL real

# ==============================================================================
# 3. FUNÇÕES AUXILIARES GLOBAIS
# ==============================================================================
@st.cache_data
def carregar_prompts_config():
    return {"versao": "1.0"}

PROMPTS_CONFIG = carregar_prompts_config()

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
    if formato == "txt": return io.BytesIO(conteudo.encode("utf-8"))
    elif formato == "docx":
        document = Document(); document.add_paragraph(conteudo); bio = io.BytesIO(); document.save(bio); bio.seek(0)
        return bio
    elif formato == "pdf":
        pdf = FPDF(); pdf.add_page(); caminho_fonte = get_asset_path("DejaVuSans.ttf")
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

    # --- 5.1: Central de Comando (MaxAdministrativo) ---
    def exibir_central_de_comando(self):
        st.header("🏢 Central de Comando")
        st.caption("Sua visão 360° para uma gestão proativa e inteligente.")

        # --- KPIs ---
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Saúde Operacional", "85%", "5%")
        with col2:
            st.metric("Progresso Estratégico", "62%", "-2%")
        with col3:
            st.metric("Clima da Equipe", "8.2/10")

        # --- Módulos Principais ---
        st.markdown("---")
        with st.expander("⚙️ Operações & Compliance (MaxAdministrativo)", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Pré-Contabilidade Inteligente")
                st.info("💡 Alerta do Max: Percebi que este mês você não lançou a nota fiscal do seu aluguel. Gostaria de criar um lembrete recorrente?")
                st.dataframe({"Transação": ["Posto Shell", "Venda #1254"],"Categoria (IA)": ["Despesa com Veículo", "Receita de Vendas"]}, use_container_width=True)
            with col2:
                st.subheader("Controle de Estoque")
                st.warning("📈 Alerta do Max: Atenção: Dia das Mães chegando. Seu estoque do 'Produto Y' não será suficiente.")
                st.progress(75, text="Produto X (75%)")
                st.progress(15, text="Produto Y (15%) - Nível Baixo!")

        with st.expander("💜 Pessoas & Cultura (MaxTrainer IA)"):
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Mural Inteligente")
                st.success("✍️ Sugestão do Max: As vendas da semana superaram a meta! Que tal compartilhar um post de parabéns para a equipe?")
            with col2:
                st.subheader("Termômetro de Clima")
                st.metric("Nível de Energia da Equipe", "8.2/10")

        with st.expander("🧭 Bússola Estratégica"):
            st.subheader("Análise SWOT Dinâmica (Sugestões da IA)")
            col1, col2 = st.columns(2)
            with col1:
                st.success("Forças: Fluxo de caixa positivo.")
                st.warning("Fraquezas: Baixa rotatividade do Produto Z.")
            with col2:
                st.info("Oportunidades: Aumento na busca por 'comida vegana'.")
                st.error("Ameaças: Novo concorrente abriu a 2km.")
            st.success("🎯 Próximo Passo Sugerido por Max: Com base na sua força (fluxo de caixa) e na oportunidade (demanda vegana), que tal criar o objetivo: 'Lançar uma nova linha de produtos veganos'?")


    # --- Demais agentes como placeholders ou funcionalidades simplificadas ---
        # --- 5.2: MaxFinanceiro ---
    def exibir_max_financeiro(self):
        st.header("💰 MaxFinanceiro")
        st.caption("O Cérebro Financeiro da sua empresa em Tempo Real.")

        # --- Abas para navegação interna do módulo ---
        tab_visao_geral, tab_detalhes, tab_precificador, tab_guardiao, tab_relatorio = st.tabs([
            "📊 Visão Geral", "💸 Fluxo de Caixa", "💡 Precificador IA", "🛡️ Guardião das Contas", "📄 Boletim Financeiro"
        ])

        # --- Dados Simulados para o Módulo ---
        state = {
            'todaySales': 1250.75,
            'accountsReceivable': 7500.50,
            'cashBalance': 12345.67,
            'transactions': pd.DataFrame({
                'Data': pd.to_datetime(pd.date_range(end=datetime.date.today(), periods=10)),
                'Descrição': ['Venda POS', 'Fornecedor ABC', 'Venda Online', 'Salários', 'Venda PIX', 'Aluguel', 'Venda POS', 'Fornecedor XYZ', 'Venda Online', 'Taxas'],
                'Tipo': ['Entrada', 'Saída', 'Entrada', 'Saída', 'Entrada', 'Saída', 'Entrada', 'Saída', 'Entrada', 'Saída'],
                'Valor': [550.20, -450.00, 890.50, -3500.00, 320.00, -1800.00, 430.10, -320.80, 1250.00, -150.45]
            }),
            'products': [
                {'id': 1, 'name': 'Prato do Dia', 'cost': 10.50, 'price': 35.00, 'sales': 25},
                {'id': 2, 'name': 'Suco Especial', 'cost': 4.00, 'price': 10.00, 'sales': 40},
                {'id': 3, 'name': 'Serviço de Consultoria', 'cost': 50.00, 'price': 250.00, 'sales': 5},
            ]
        }

        # --- Conteúdo da Aba: Visão Geral ---
        with tab_visao_geral:
            st.subheader("Painel de Controle Financeiro")
            col1, col2, col3 = st.columns(3)
            col1.metric("Vendas do Dia", f"R$ {state['todaySales']:,.2f}", "12%")
            col2.metric("Contas a Receber", f"R$ {state['accountsReceivable']:,.2f}")
            col3.metric("Saldo em Caixa", f"R$ {state['cashBalance']:,.2f}", "- R$ 250,00")
            
            st.markdown("---")
            
            col1, col2 = st.columns([2, 1])
            with col1:
                st.subheader("Fluxo de Caixa (Últimos 30 dias)")
                # Gráfico de Fluxo de Caixa
                df_cashflow = state['transactions'].copy()
                df_cashflow['Data'] = pd.to_datetime(df_cashflow['Data'])
                df_cashflow['Entrada'] = df_cashflow['Valor'].clip(lower=0)
                df_cashflow['Saída'] = df_cashflow['Valor'].clip(upper=0).abs()
                df_cashflow = df_cashflow.groupby(pd.Grouper(key='Data', freq='D'))[['Entrada', 'Saída']].sum().reset_index()

                fig = go.Figure()
                fig.add_trace(go.Bar(x=df_cashflow['Data'], y=df_cashflow['Entrada'], name='Entradas', marker_color='#10b981'))
                fig.add_trace(go.Bar(x=df_cashflow['Data'], y=df_cashflow['Saída'], name='Saídas', marker_color='#ef4444'))
                fig.update_layout(barmode='group', xaxis_title='Data', yaxis_title='Valor (R$)', margin=dict(l=20, r=20, t=20, b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                st.subheader("💡 Alertas do Agente Max")
                with st.container(border=True):
                    st.warning("Atenção: se o ritmo de saídas continuar, seu caixa pode ficar negativo em aprox. 12 dias.")
                with st.container(border=True):
                    st.success("Seu 'Suco Especial' tem uma margem baixa. Que tal criar um combo com o 'Prato do Dia'?")

        # --- Conteúdo da Aba: Fluxo de Caixa Detalhado ---
        with tab_detalhes:
            st.subheader("Últimas Transações Registradas")
            st.dataframe(state['transactions'].style.format({"Valor": "R$ {:,.2f}"}), use_container_width=True)

        # --- Conteúdo da Aba: Precificador IA ---
        with tab_precificador:
            st.subheader("Análise de Margem por Produto")
            for prod in state['products']:
                margin = ((prod['price'] - prod['cost']) / prod['price']) * 100
                with st.container(border=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**{prod['name']}**")
                        st.caption(f"Preço: R$ {prod['price']:.2f} | Custo: R$ {prod['cost']:.2f}")
                    with col2:
                        st.metric("Margem de Contribuição", f"{margin:.1f}%", delta=f"{(margin-50):.1f}% vs Meta" if margin < 50 else None)

        # --- Conteúdo da Aba: Guardião das Contas ---
        with tab_guardiao:
            st.subheader("Monitoramento de Transações")
            st.info("O Agente Max monitora suas contas e sinaliza transações que precisam de atenção.")
            with st.container(border=True):
                st.error("⚠️ **Despesa Suspeita:** Identificamos uma compra de R$ 55,90 na 'Netflix.com' com o cartão da empresa. Esta parece ser uma despesa pessoal. Recomendo reclassificar ou reembolsar.")
            with st.container(border=True):
                st.write("✅ **Transação Normal:** Compra de R$ 450,00 no 'Fornecedor ABC' (Conta PJ).")

        # --- Conteúdo da Aba: Boletim Financeiro ---
        with tab_relatorio:
            st.subheader("Seu Check-up Financeiro Mensal")
            dre_simplificada = f"""
            **DRE Simplificada (Últimos 30 dias)**
            --------------------------------------
            Receita Total: R$ 25,450.00
            Custos Variáveis: (R$ 8,100.00)
            --------------------------------------
            Margem de Contribuição: R$ 17,350.00
            Despesas Fixas: (R$ 11,500.00)
            --------------------------------------
            **Lucro Operacional: R$ 5,850.00**
            """
            st.code(dre_simplificada, language="markdown")
            
            st.download_button(
                label="📥 Gerar Relatório para Crédito (PDF)",
                data="Este é um relatório simplificado gerado pelo Max IA.", # A lógica de geração do PDF já existe
                file_name="relatorio_credito_max_ia.txt",
                mime="text/plain",
                use_container_width=True
            )

        # --- 5.3: Central do Cliente 360° ---
    def exibir_central_cliente(self):
        st.header("📈 Central do Cliente 360°")
        st.caption("Transforme dados em relacionamentos e fidelização.")

        # --- KPIs ---
        col1, col2, col3 = st.columns(3)
        col1.metric("Satisfação (NPS)", "72", "Excelente")
        col2.metric("Taxa de Retenção", "85%")
        col3.metric("Clientes em Risco", "18")

        st.markdown("---")

        # --- Módulos Principais ---
        col1, col2 = st.columns([2, 1])

        with col1:
            st.subheader("👥 Cadastro de Clientes Unificado")
            # Dados simulados para a tabela
            customer_data = {
                'Cliente': ['Maria Silva', 'João Pereira', 'Ana Costa', 'Carlos Souza'],
                'Última Compra': ['08/06/2025', '05/06/2025', '10/02/2025', '09/06/2025'],
                'Status': ['Campeão', 'Fiel', 'Em Risco', 'Novo'],
                'Ticket Médio': [150.75, 89.90, 45.50, 199.00]
            }
            df_customers = pd.DataFrame(customer_data)
            st.dataframe(df_customers, use_container_width=True)
            st.info("💡 Insight do Max: Vejo que a Maria Silva (cliente 'Campeão') sempre compra o 'Produto X'. Que tal oferecer o 'Produto Y', que é complementar, com um desconto?")


        with col2:
            st.subheader("📊 Análise de Sentimentos")
            # Dados simulados para o gráfico
            sentiment_data = pd.DataFrame({
                'Tópico': ['Atendimento', 'Preço', 'Entrega'],
                'Positivo': [15, 5, 10],
                'Negativo': [2, 8, 5]
            }).set_index('Tópico')
            st.bar_chart(sentiment_data, color=["#10b981", "#ef4444"])


        st.markdown("---")
        st.subheader("🎯 Campanhas de Fidelidade Sugeridas pela IA")
        col1, col2 = st.columns(2)
        with col1:
            with st.container(border=True):
                st.success("**Para Clientes 'Campeões'**")
                st.write("Que tal criar um 'Clube VIP' para seus 8 melhores clientes com um desconto exclusivo?")
                if st.button("Criar Campanha VIP"):
                    st.toast("Campanha VIP criada!")

        with col2:
            with st.container(border=True):
                st.warning("**Para Clientes 'Em Risco'**")
                st.write("Vamos enviar uma campanha de reativação com o título 'Estamos com saudades!' e frete grátis?")
                if st.button("Criar Campanha de Reativação"):
                     st.toast("Campanha de Reativação enviada!")
        # --- 5.5: Max Construtor ---
    def exibir_max_construtor(self):
        st.header("🏗️ Max Construtor")
        st.caption("Crie páginas de venda de alta conversão com poucos cliques.")
        st.markdown("---")

        # Inicializar o estado da sessão para o construtor
        if 'construtor_state' not in st.session_state:
            st.session_state.construtor_state = {
                'theme_color': 'Azul Moderno',
                'theme_font': 'Poppins',
                'logo_b64': None,
                'header_pitch': 'A solução definitiva para o seu negócio crescer!',
                'whatsapp': '',
                'youtube': '',
                'instagram': '',
                'facebook': '',
                'products': [],
                'footer_text': f"© {datetime.date.today().year} Sua Empresa | Todos os direitos reservados."
            }
        
        state = st.session_state.construtor_state

        # --- Layout de duas colunas ---
        col1, col2 = st.columns([1, 1.2])

        # --- COLUNA 1: Painel de Controle ---
        with col1:
            st.subheader("Painel de Controle")

            with st.expander("1. Configurações Gerais", expanded=True):
                state['theme_color'] = st.selectbox("Paleta de Cores", ["Azul Moderno", "Verde Crescimento", "Roxo Inovação", "Cinza Corporativo"])
                state['theme_font'] = st.selectbox("Fonte", ["Poppins", "Roboto", "Lato", "Open Sans"])

            with st.expander("2. Cabeçalho e Logo", expanded=True):
                uploaded_logo = st.file_uploader("Logomarca (PNG, JPG)", type=['png', 'jpg'])
                if uploaded_logo:
                    state['logo_b64'] = base64.b64encode(uploaded_logo.getvalue()).decode()
                state['header_pitch'] = st.text_area("Pitch de Vendas (abertura)", value=state['header_pitch'])

            with st.expander("3. Links e Contato"):
                state['whatsapp'] = st.text_input("Nº WhatsApp (Ex: 5511912345678)", value=state['whatsapp'])
                state['youtube'] = st.text_input("URL YouTube", value=state['youtube'])
                state['instagram'] = st.text_input("URL Instagram", value=state['instagram'])
                state['facebook'] = st.text_input("URL Facebook", value=state['facebook'])

            with st.expander("4. Produtos/Serviços"):
                with st.form("product_form"):
                    st.write("Adicionar novo produto/serviço")
                    product_name = st.text_input("Nome do Produto")
                    product_photo = st.file_uploader("Foto do Produto", type=['png', 'jpg'])
                    product_desc = st.text_area("Descrição")
                    submitted = st.form_submit_button("Adicionar Produto")
                    if submitted and product_name and product_photo and product_desc:
                        if len(state['products']) < 18:
                            photo_b64 = base64.b64encode(product_photo.getvalue()).decode()
                            state['products'].append({
                                'name': product_name,
                                'photo_b64': photo_b64,
                                'desc': product_desc
                            })
                            st.success(f"Produto '{product_name}' adicionado!")
                        else:
                            st.warning("Limite de 18 produtos atingido.")
                
                if state['products']:
                    st.write("Produtos Adicionados:")
                    for i, prod in enumerate(state['products']):
                        c1, c2 = st.columns([3, 1])
                        c1.write(f"_{prod['name']}_")
                        if c2.button("Remover", key=f"del_{i}", use_container_width=True):
                            state['products'].pop(i)
                            st.rerun()


            with st.expander("5. Rodapé"):
                state['footer_text'] = st.text_input("Texto de Assinatura/Contato", value=state['footer_text'])

        # --- COLUNA 2: Pré-visualização ---
        with col2:
            st.subheader("Pré-visualização da Página")

            # Mapeamento de temas para cores
            color_map = {
                'Azul Moderno': {'primary': '#2563eb', 'secondary': '#dbeafe', 'text': '#1e40af', 'bg': '#eff6ff'},
                'Verde Crescimento': {'primary': '#16a34a', 'secondary': '#dcfce7', 'text': '#14532d', 'bg': '#f0fdf4'},
                'Roxo Inovação': {'primary': '#7c3aed', 'secondary': '#f3e8ff', 'text': '#581c87', 'bg': '#faf5ff'},
                'Cinza Corporativo': {'primary': '#475569', 'secondary': '#e2e8f0', 'text': '#1e293b', 'bg': '#f8fafc'},
            }
            font_map = {
                'Poppins': 'Poppins, sans-serif',
                'Roboto': 'Roboto, sans-serif',
                'Lato': 'Lato, sans-serif',
                'Open Sans': 'Open Sans, sans-serif'
            }

            colors = color_map[state['theme_color']]
            font_family = font_map[state['theme_font']]

            # Montando o HTML da pré-visualização
            logo_html = f"<img src='data:image/png;base64,{state['logo_b64']}' style='max-height: 80px; margin: 0 auto 1rem;'>" if state['logo_b64'] else ""
            
            social_links_html = ""
            if any([state['youtube'], state['instagram'], state['facebook']]):
                social_links_html += "<div style='display: flex; justify-content: center; gap: 1rem; margin-top: 1rem;'>"
                if state['youtube']: social_links_html += "<a href='#' style='font-size: 2rem; text-decoration: none;'>▶️</a>"
                if state['instagram']: social_links_html += "<a href='#' style='font-size: 2rem; text-decoration: none;'>📸</a>"
                if state['facebook']: social_links_html += "<a href='#' style='font-size: 2rem; text-decoration: none;'>👍</a>"
                social_links_html += "</div>"

            products_html = ""
            if state['products']:
                for prod in state['products']:
                    products_html += f"""
                    <div style="background-color: {colors['bg']}; border-left: 4px solid {colors['primary']}; border-radius: 8px; padding: 1rem; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                        <img src="data:image/png;base64,{prod['photo_b64']}" style="width: 100%; height: 150px; object-fit: cover; border-radius: 4px; margin-bottom: 1rem;">
                        <h4 style="font-weight: bold; color: {colors['text']}; margin: 0 0 0.5rem 0;">{prod['name']}</h4>
                        <p style="font-size: 0.9rem; color: #4a5568;">{prod['desc']}</p>
                    </div>
                    """
            else:
                products_html = "<p style='text-align: center; color: #9ca3af;'>Seus produtos aparecerão aqui.</p>"

            whatsapp_html = ""
            if state['whatsapp']:
                whatsapp_html = f"""
                <div style='text-align: center; margin-top: 2rem;'>
                    <a href='#' style='background-color: {colors['primary']}; color: white; padding: 0.75rem 1.5rem; border-radius: 9999px; text-decoration: none; font-weight: bold;'>
                        Fale Conosco no WhatsApp
                    </a>
                </div>
                """

            # Container da pré-visualização com estilo de folha A4
            with st.container():
                html_to_render = f"""
                <div style="border: 1px solid #e2e8f0; box-shadow: 0 10px 25px rgba(0,0,0,0.1); font-family: {font_family}; aspect-ratio: 210/297; padding: 2rem; background-color: white;">
                    <header style="background-color: {colors['primary']}; color: white; text-align: center; padding: 2rem; border-radius: 8px 8px 0 0;">
                        {logo_html}
                        <h2 style="font-size: 1.8rem; font-weight: bold; margin: 0;">{state['header_pitch']}</h2>
                        {social_links_html}
                    </header>
                    <main style="padding: 2rem 0;">
                        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem;">
                            {products_html}
                        </div>
                        {whatsapp_html}
                    </main>
                    <footer style="background-color: {colors['secondary']}; text-align: center; padding: 1rem; font-size: 0.75rem; color: #374151; border-top: 2px solid {colors['primary']}; border-radius: 0 0 8px 8px;">
                        {state['footer_text']}
                    </footer>
                </div>
                """
                st.markdown(html_to_render, unsafe_allow_html=True)

        # --- Ação de Download ---
        # A lógica de download em PDF precisaria ser reimplementada em Python
        # Esta é uma versão simplificada
        st.download_button(
            label="📥 Baixar Página em PDF (Simplificado)",
            data="Esta é uma prévia. A funcionalidade completa de PDF usaria os dados acima.",
            file_name="pagina_vendas.txt",
            mime="text/plain",
            use_container_width=True
        )

    def exibir_max_marketing_total(self): st.info("🚀 Agente MaxMarketing Total em desenvolvimento.")
        # --- 5.4: MaxTrainer IA ---
    def exibir_max_trainer_ia(self):
        st.title("🎓 MaxTrainer IA")
        st.markdown("Seu mentor pessoal para descomplicar a jornada empreendedora.")

        # Inicializa o histórico do chat se não existir
        if "messages_trainer" not in st.session_state:
            st.session_state.messages_trainer = [{"role": "assistant", "content": "Olá! Eu sou seu mentor pessoal de IA. Sobre qual conceito de negócios você gostaria de aprender hoje? Tente perguntar 'O que é Fluxo de Caixa?' ou 'Explique Análise SWOT'."}]

        # Exibe as mensagens do histórico
        for message in st.session_state.messages_trainer:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Input do usuário
        if prompt := st.chat_input("Pergunte sobre DRE, Fluxo de Caixa, Marketing..."):
            # Adiciona a mensagem do usuário ao histórico e exibe
            st.session_state.messages_trainer.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # Gera e exibe a resposta do assistente
            with st.chat_message("assistant"):
                with st.spinner("MaxTrainer está pensando na melhor analogia..."):
                    try:
                        # Em um app real, aqui você buscaria o domínio de analogia do usuário no Firebase
                        analogy_domain = "futebol" # Usando um domínio fixo para este exemplo

                        # Lógica da IA para gerar a resposta (simulada aqui)
                        # O prompt real seria enviado ao LLM, como no seu código original
                        if "fluxo de caixa" in prompt.lower():
                            full_response = f"Ótima pergunta! Pensando em **{analogy_domain}**, o Fluxo de Caixa é como o **fôlego de um jogador**. As **entradas** (vendas) são os momentos de descanso e hidratação. As **saídas** (despesas) são os piques e corridas. Se ele corre mais do que descansa, uma hora fica sem fôlego! Nosso objetivo é manter seu 'jogador' com fôlego de campeão o tempo todo!"
                        elif "swot" in prompt.lower():
                            full_response = f"Excelente! Usando nossa analogia de **{analogy_domain}**, a Análise SWOT é como um técnico analisando seu time. **Forças**: seu atacante artilheiro. **Fraquezas**: a defesa que toma muitos gols. **Oportunidades**: o time adversário tem um jogador importante lesionado. **Ameaças**: o próximo jogo é fora de casa, com chuva forte."
                        else:
                            full_response = "Desculpe, ainda estou aprendendo sobre isso. Que tal tentarmos falar sobre 'Fluxo de Caixa' ou 'Análise SWOT'?"

                        st.markdown(full_response)
                        # Adiciona a resposta da IA ao histórico
                        st.session_state.messages_trainer.append({"role": "assistant", "content": full_response})

                    except Exception as e:
                        st.error(f"Ocorreu um erro ao contatar a IA: {e}")
    
    # --- Métodos de Onboarding (simplificados para o contexto) ---
    def exibir_onboarding_calibracao(self):
        st.title("Vamos calibrar o seu Max IA Empresarial! ⚙️")
        with st.form(key="calibration_form"):
            company_name = st.text_input("Nome da Sua Empresa")
            setor = st.selectbox("Setor de Atuação", ["Varejo", "Serviços", "Alimentação", "Outro"])
            if st.form_submit_button("Criar e Continuar", use_container_width=True):
                if not company_name: st.warning("O nome da empresa é essencial.")
                else: st.success("Empresa configurada!"); time.sleep(1); st.rerun()

    def exibir_onboarding_trainer(self):
        st.title("Quase lá! Vamos personalizar sua experiência.")
        st.selectbox("Escolha um assunto para analogias:", ["Futebol", "Culinária", "Carros"], key="analogy_choice")
        if st.button("Salvar e Começar a Usar!", use_container_width=True): st.success("Preferência salva!"); time.sleep(1); st.rerun()
            
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
        else: st.title("Max IA Empresarial")
        
        st.header("Acesse sua Central de Comando")
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
                        except Exception as e: st.error("Este e-mail já está em uso ou ocorreu um erro.")
                    else: st.warning("Preencha todos os campos corretamente.")

# ==============================================================================
# 7. ESTRUTURA PRINCIPAL E EXECUÇÃO DO APP
# ==============================================================================
def main():
    if not all([pb_auth_client, firestore_db]):
        st.error("Falha crítica na inicialização dos serviços."); st.stop()

    user_is_authenticated, user_uid, user_email = get_current_user_status(pb_auth_client)

    if user_is_authenticated:
        # ---- Início do Bloco Corrigido ----
        logo_path = get_asset_path('max-ia-lgo.fundo.transparente.png')
        if os.path.exists(logo_path):
            st.sidebar.image(logo_path, width=100)
        
        st.sidebar.title("Max IA Empresarial")
        st.sidebar.markdown("---")
        
        if 'agente' not in st.session_state:
            llm = get_llm()
            if llm and firestore_db: 
                st.session_state.agente = MaxAgente(llm, firestore_db)
            else: 
                st.error("Agente Max IA não pôde ser inicializado."); st.stop()
        
        agente = st.session_state.agente
        
        try:
            user_doc = firestore_db.collection(USER_COLLECTION).document(user_uid).get()
            user_data = user_doc.to_dict() if user_doc.exists else None
        except Exception as e: 
            st.error(f"Erro ao buscar dados do usuário: {e}"); st.stop()

        if not user_data: 
            user_data = {"email": user_email, "access_level": 2}
            firestore_db.collection(USER_COLLECTION).document(user_uid).set(user_data, merge=True)
        
        st.sidebar.write(f"Logado como: **{user_email}**")
        st.sidebar.caption(f"Nível de Acesso: {user_data.get('access_level', 'N/D')}")
        if st.sidebar.button("Logout", key=f"{APP_KEY_SUFFIX}_logout"):
            st.session_state.clear(); st.rerun()
        
        opcoes_menu = {
            "👋 Bem-vindo": agente.exibir_painel_boas_vindas,
            "🏢 Central de Comando": agente.exibir_central_de_comando,
            "💰 MaxFinanceiro": agente.exibir_max_financeiro,
            "📈 Central do Cliente 360°": agente.exibir_central_cliente,
            "🚀 MaxMarketing Total": agente.exibir_max_marketing_total,
            "🎓 MaxTrainer IA": agente.exibir_max_trainer_ia,
            "🏗️ MaxConstrutor": agente.exibir_max_construtor,
        }
        
        if user_data.get('access_level') != 1:
            opcoes_a_remover = ["💰 MaxFinanceiro", "🏢 Central de Comando"]
            for opcao in opcoes_a_remover:
                if opcao in opcoes_menu: del opcoes_menu[opcao]

        selecao_label = st.sidebar.radio("Max Agentes IA:", list(opcoes_menu.keys()), key=f"{APP_KEY_SUFFIX}_menu")
        opcoes_menu[selecao_label]()
        # ---- Fim do Bloco Corrigido ----

    else:
        # Bloco do usuário não logado (permanece igual)
        if st.session_state.get('show_login_form', False):
            exibir_formularios_de_acesso()
        else:
            exibir_pagina_de_entrada()

if __name__ == "__main__":
    main()
