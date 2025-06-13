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
    # O PWD (Print Working Directory) garante que o caminho é relativo ao local do script.
    try:
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), ASSETS_DIR, asset_name)
    except NameError:
         # Fallback para ambientes onde __file__ não está definido (como alguns notebooks)
        return os.path.join(ASSETS_DIR, asset_name)


# Tenta carregar o ícone da página, com fallback
try:
    page_icon_path = get_asset_path("carinha-agente-max-ia.png")
    page_icon_obj = Image.open(page_icon_path) if os.path.exists(page_icon_path) else "🤖"
except Exception:
    page_icon_obj = "🤖"
st.set_page_config(page_title="Max IA Empresarial", page_icon=page_icon_obj, layout="wide", initial_sidebar_state="collapsed")
# --- FIM DA CONFIGURAÇÃO DE CAMINHOS ---

# ==============================================================================
# 2. CONSTANTES
# ==============================================================================
APP_KEY_SUFFIX = "maxia_app_v14.0_final_build"
USER_COLLECTION = "users"
COMPANY_COLLECTION = "companies"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
SALES_PAGE_URL = "https://sua-pagina-de-vendas.com.br" # <-- IMPORTANTE: Substitua por sua URL real

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
# 5. CLASSE PRINCIPAL DO AGENTE (FUNCIONALIDADES COMPLETAS)
# ==============================================================================
class MaxAgente:
    def __init__(self, llm_instance, db_firestore_instance):
        self.llm = llm_instance
        self.db = db_firestore_instance

        # --- NOVO: Função de Onboarding e Calibração ---
    def exibir_onboarding_calibracao(self):
        st.title("Checklist de Calibração – Max IA Empresarial ⚙️")
        st.markdown("Para que nossos agentes de IA atuem como membros da sua equipe, precisamos conhecer sua empresa a fundo. Suas respostas são essenciais para calibrar a inteligência e as prioridades dos seus novos assistentes virtuais.")
        st.progress(0, text="Etapa 1 de 6")

        if 'calibration_data' not in st.session_state:
            st.session_state.calibration_data = {}

        with st.form(key="calibration_form"):
            st.header("Seção 1: Identidade e DNA da Empresa")
            st.session_state.calibration_data['company_name'] = st.text_input("Nome da Empresa:")
            st.session_state.calibration_data['website'] = st.text_input("Website e @ das principais redes sociais:")
            st.session_state.calibration_data['setor'] = st.text_input("Setor de Atuação:", placeholder="Ex: Varejo de moda, restaurante, agência de marketing...")
            st.session_state.calibration_data['pitch'] = st.text_area("Descreva seu negócio em uma frase:", placeholder="Ex: Vendemos cosméticos veganos para o público jovem pela internet.")
            st.session_state.calibration_data['valores'] = st.multiselect("Quais são os 3 principais valores da sua marca?", ["Agilidade", "Sustentabilidade", "Atendimento humanizado", "Inovação", "Tradição", "Qualidade"])
            st.session_state.calibration_data['personalidade'] = st.radio("Qual adjetivo melhor descreve a personalidade da sua marca?", 
                                                                         ('Divertida e Jovem', 'Séria e Corporativa', 'Acolhedora e Amigável', 'Sofisticada e Premium', 'Técnica e Especialista', 'Inovadora e Ousada'))

            st.header("Seção 2: Produtos, Serviços e Proposta de Valor")
            st.session_state.calibration_data['produtos'] = st.text_area("Liste seus 3 principais produtos ou serviços:")
            st.session_state.calibration_data['diferencial'] = st.text_input("Qual é o principal diferencial competitivo da sua empresa?")
            st.session_state.calibration_data['faixa_preco'] = st.radio("Qual é a faixa de preço dos seus produtos/serviços?", ('Baixo Custo / Acessível', 'Preço Médio / Competitivo', 'Alto Valor / Premium'))

            st.header("Seção 3: O Cliente Ideal (Público-Alvo)")
            st.session_state.calibration_data['cliente_ideal'] = st.text_area("Descreva seu cliente ideal:", placeholder="Idade, gênero, localização, interesses...")
            st.session_state.calibration_data['dor_cliente'] = st.text_input("Qual a principal 'dor' ou necessidade do seu cliente que sua empresa resolve?")
            st.session_state.calibration_data['linguagem_cliente'] = st.radio("Qual é a linguagem que mais conecta com seu público?", ('Informal, com gírias e emojis 😄', 'Padrão, clara e objetiva.', 'Formal e técnica.'))
            
            st.header("Seção 4: Marketing e Vendas")
            st.session_state.calibration_data['canais_atracao'] = st.multiselect("Quais são seus principais canais para atrair clientes hoje?", 
                                                                                ['Loja Física', 'Vendedores Externos', 'Anúncios no Google', 'Anúncios em Redes Sociais', 'Conteúdo Orgânico', 'Indicações', 'WhatsApp', 'E-mail Marketing'])
            st.session_state.calibration_data['objecao_venda'] = st.text_input("Qual a objeção de venda mais comum que vocês enfrentam?", placeholder="Ex: 'Está caro', 'Vou pensar'...")

            st.header("Seção 5: Operações e Atendimento")
            st.session_state.calibration_data['faqs'] = st.text_area("Quais são as 3 perguntas mais frequentes que sua equipe de atendimento recebe?")
            st.session_state.calibration_data['tarefa_repetitiva'] = st.text_input("Qual tarefa repetitiva você mais gostaria que a IA assumisse?")

            st.header("Seção 6: Objetivos e Calibração Final da IA")
            st.session_state.calibration_data['objetivo_principal'] = st.radio("Qual é o OBJETIVO Nº 1 que você espera alcançar com o Max Ia Empresarial nos próximos 3 meses?",
                                                                               ('Aumentar o número de leads', 'Aumentar as vendas', 'Reduzir o tempo de resposta ao cliente', 'Automatizar tarefas manuais'))
            st.session_state.calibration_data['autonomia_ia'] = st.slider("Em uma escala de 1 a 5, quão autônomo você deseja que os agentes de IA sejam?", 1, 5, 3, 
                                                                         help="1 = Apenas sugere; 3 = Executa tarefas padrão; 5 = Toma decisões de forma independente.")
            
            submitted = st.form_submit_button("✅ Concluir Calibração e Ativar meus Agentes!")
            if submitted:
                with st.spinner("Salvando o DNA da sua empresa e calibrando seus agentes de IA..."):
                    try:
                        user_uid = st.session_state.get('user_uid')
                        company_ref = self.db.collection(COMPANY_COLLECTION).document()
                        # Salva os dados da empresa
                        company_ref.set(st.session_state.calibration_data)
                        
                        # Atualiza o documento do usuário com o ID da nova empresa
                        user_ref = self.db.collection(USER_COLLECTION).document(user_uid)
                        user_ref.update({"company_id": company_ref.id})

                        time.sleep(2)
                        st.success("Calibração concluída! Seus agentes agora conhecem o seu negócio.")
                        time.sleep(1)
                        # Limpa os dados do formulário para a próxima vez
                        del st.session_state['calibration_data']
                        st.rerun()
                    except Exception as e:
                        st.error(f"Ocorreu um erro ao salvar a calibração: {e}")


    def exibir_painel_boas_vindas(self):
        st.title("👋 Bem-vindo ao seu Centro de Comando!")
        st.markdown("Use o menu à esquerda para navegar entre os Agentes Max IA e transformar a gestão da sua empresa.")
        try:
            logo_path = get_asset_path('max-ia-lgo.fundo.transparente.png')
            if os.path.exists(logo_path):
                st.image(logo_path, width=200)
        except Exception as e:
            print(f"Alerta: Não foi possível carregar a logo do painel de boas-vindas. Erro: {e}")

    def exibir_central_de_comando(self):
        st.header("🏢 Central de Comando")
        st.caption("Sua visão 360° para uma gestão proativa e inteligente.")
        col1, col2, col3 = st.columns(3)
        col1.metric("Saúde Operacional", "85%", "5%")
        col2.metric("Progresso Estratégico", "62%", "-2%")
        col3.metric("Clima da Equipe", "8.2/10")
        with st.expander("⚙️ Operações & Compliance (MaxAdministrativo)", expanded=True):
            st.info("💡 Alerta do Max: Percebi que este mês você não lançou a nota fiscal do seu aluguel.")
        
    def exibir_max_financeiro(self):
        st.header("💰 MaxFinanceiro")
        st.caption("O Cérebro Financeiro da sua empresa em Tempo Real.")
        col1, col2, col3 = st.columns(3)
        col1.metric("Vendas do Dia", "R$ 1.250,75", "12%")
        col2.metric("Contas a Receber", "R$ 7.500,50")
        col3.metric("Saldo em Caixa", "R$ 12.345,67", "- R$ 250,00")
        with st.expander("💡 Alertas e Insights do MaxFinanceiro"):
            st.warning("Atenção: sua projeção de caixa indica um possível saldo negativo em 12 dias.")

    def exibir_central_cliente(self):
        st.header("📈 Central do Cliente 360°")
        st.caption("Transforme dados em relacionamentos e fidelização.")
        col1, col2, col3 = st.columns(3)
        col1.metric("Satisfação (NPS)", "72", "Excelente")
        col2.metric("Taxa de Retenção", "85%")
        col3.metric("Clientes em Risco", "18")
        with st.expander("🎯 Campanhas de Fidelidade Sugeridas pela IA", expanded=True):
            st.success("**Para Clientes 'Campeões'**: Que tal criar um 'Clube VIP' com desconto exclusivo?")
            st.info("**Para Clientes 'Em Risco'**: Vamos enviar uma campanha de reativação com o título 'Estamos com saudades!'?")

    def exibir_max_trainer_ia(self):
        st.title("🎓 MaxTrainer IA")
        st.markdown("Seu mentor pessoal para descomplicar a jornada empreendedora.")
        if "messages_trainer" not in st.session_state:
            st.session_state.messages_trainer = [{"role": "assistant", "content": "Olá! Sobre o que vamos conversar hoje?"}]
        for message in st.session_state.messages_trainer:
            with st.chat_message(message["role"]): st.markdown(message["content"])
        if prompt := st.chat_input("Pergunte sobre Fluxo de Caixa..."):
            st.session_state.messages_trainer.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
            with st.chat_message("assistant"):
                st.markdown(f"Explicando '{prompt}' com uma analogia de Futebol... (Simulação)")
                st.session_state.messages_trainer.append({"role": "assistant", "content": f"Explicando '{prompt}' com uma analogia de Futebol... (Simulação)"})

            # --- 5.1: MaxMarketing Total ---
    def exibir_max_marketing_total(self):
        st.header("🚀 Estúdio de Criação Max")
        st.caption("Seu Diretor de Marketing Pessoal para criar posts, campanhas e anúncios que vendem.")
        st.markdown("---")
        
        # --- Estrutura de Abas (Wizard) ---
        tab_post, tab_campaign, tab_ads = st.tabs([
            "✍️ Criar Post Rápido", "🎯 Criar Campanha Completa", "⚡ Criar Anúncio Rápido"
        ])

        # --- Aba 1: Criar Post ---
        with tab_post:
            st.subheader("Gerador de Conteúdo Criativo")
            st.write("Ideal para manter suas redes sociais ativas e interessantes no dia a dia.")

            # Usar o st.session_state para guardar o resultado
            if 'marketing_post_result' not in st.session_state:
                st.session_state.marketing_post_result = None

            with st.form("post_briefing_form"):
                post_idea = st.text_area("Sobre o que é o post de hoje? Me dê uma ideia simples.", "Promoção prato do dia: arroz, feijão, batata frita, salada de tomate, alface e cebola e bife de boi por APENAS 18,99")
                post_channel = st.selectbox("Para qual canal você quer criar primeiro?", ["Instagram", "Facebook", "TikTok", "YouTube (Roteiro Curto)"])
                
                submitted = st.form_submit_button("💡 Gerar Pacote de Mídia com Max IA")
                if submitted:
                    with st.spinner("Max está buscando inspiração e criando seu conteúdo..."):
                        # --- LÓGICA DA IA (SIMULADA, MAS AGORA USANDO O INPUT) ---
                        # Em um app real, aqui você chamaria self.llm.invoke(prompt)
                        time.sleep(2) 
                        
                        # Extrai o tópico principal do input do usuário para usar no título
                        topic = post_idea.split(':')[0].replace("Promoção", "").strip() if ':' in post_idea else "seu produto"

                        # Cria um pacote de resultados dinâmico
                        st.session_state.marketing_post_result = {
                            "topic": topic,
                            "feed_option_1": f"🍲 Sabor de casa com preço de amigo! Nosso incrível **{topic}** está em promoção por um preço que você não vai acreditar. Venha matar a fome com a gente!",
                            "feed_option_2": f"🔥 Cansado de pensar no almoço? A decisão ficou fácil! **{topic}** completo e delicioso esperando por você. Corra que a promoção é por tempo limitado!",
                            "hashtags": f"#{topic.replace(' ', '').lower()} #comidacaseira #promo #almoco #restaurante",
                            "stories_script": f"""
Cena 1 (2s): Imagem de um prato fumegante de {topic}.
   Texto na tela: "A fome bateu?"

Cena 2 (3s): Close nos ingredientes frescos do prato.
   Texto: "Qualidade que você vê e sente!"

Cena 3 (5s): Preço 'R$ 18,99' piscando na tela.
   Texto: "Seu almoço resolvido. Peça agora!" """,
                            "image_url": "https://images.pexels.com/photos/1640777/pexels-photo-1640777.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=1",
                            "image_caption": f"Imagem gerada por IA: 'Um delicioso e convidativo {topic} servido em uma mesa de restaurante'."
                        }
            
            # Exibe o resultado se ele existir no session_state
            if st.session_state.marketing_post_result:
                result = st.session_state.marketing_post_result
                st.markdown("---")
                st.subheader(f"✅ Seu Pacote de Mídia para '{result['topic']}'")

                tab_feed, tab_stories, tab_image = st.tabs(["📷 Para o Feed", "📱 Para Stories/Reels", "🖼️ Sugestão de Imagem (IA)"])

                with tab_feed:
                    st.write("**Opção 1 (Foco no Sabor):**")
                    st.info(result['feed_option_1'])
                    st.write("**Opção 2 (Foco na Praticidade):**")
                    st.warning(result['feed_option_2'])
                    st.write("**Hashtags Sugeridas:**")
                    st.caption(result['hashtags'])

                with tab_stories:
                    st.write("**Roteiro para Vídeo Curto (15s):**")
                    st.code(result['stories_script'], language="markdown")

                with tab_image:
                    st.image(result['image_url'], caption=result['image_caption'])
                
                if st.button("✨ Criar Novo Post"):
                    st.session_state.marketing_post_result = None
                    st.rerun()

        # --- Aba 2: Criar Campanha ---
        with tab_campaign:
            st.subheader("Estrategista de Mídia Digital")
            # O restante do código desta aba permanece o mesmo...
            st.info("Funcionalidade em desenvolvimento.")


        # --- Aba 3: Criar Anúncio Rápido ---
        with tab_ads:
            st.subheader("Especialista Google Simplificado")
            # O restante do código desta aba permanece o mesmo...
            st.info("Funcionalidade em desenvolvimento.")

        # --- 5.2: Max Construtor - Página de Venda ---
    def exibir_max_construtor(self):
        st.header("🏗️ Max Construtor")
        st.caption("Crie páginas de venda de alta conversão com poucos cliques.")
        st.markdown("---")

        # Inicializar o estado da sessão para o construtor se não existir
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
            st.subheader("Painel de Controle 🎛️")

            with st.expander("1. Configurações Gerais", expanded=True):
                state['theme_color'] = st.selectbox("Paleta de Cores", ["Azul Moderno", "Verde Crescimento", "Roxo Inovação", "Cinza Corporativo"], key="constr_color")
                state['theme_font'] = st.selectbox("Fonte", ["Poppins", "Roboto", "Lato", "Open Sans"], key="constr_font")

            with st.expander("2. Cabeçalho e Logo", expanded=True):
                uploaded_logo = st.file_uploader("Sua Logomarca (PNG, JPG)", type=['png', 'jpg'], key="constr_logo")
                if uploaded_logo:
                    state['logo_b64'] = base64.b64encode(uploaded_logo.getvalue()).decode()
                state['header_pitch'] = st.text_area("Pitch de Vendas (título)", value=state['header_pitch'], key="constr_pitch")

            with st.expander("3. Links e Contato"):
                state['whatsapp'] = st.text_input("Nº WhatsApp (Ex: 5511912345678)", value=state['whatsapp'], key="constr_wpp")
                state['youtube'] = st.text_input("URL YouTube", value=state['youtube'], key="constr_yt")
                state['instagram'] = st.text_input("URL Instagram", value=state['instagram'], key="constr_ig")
                state['facebook'] = st.text_input("URL Facebook", value=state['facebook'], key="constr_fb")

            with st.expander("4. Produtos/Serviços"):
                with st.form("product_form"):
                    st.write("**Adicionar novo produto/serviço**")
                    product_name = st.text_input("Nome do Produto")
                    product_photo = st.file_uploader("Foto do Produto", type=['png', 'jpg'])
                    product_desc = st.text_area("Descrição do Produto")
                    submitted = st.form_submit_button("Adicionar Produto")
                    if submitted and product_name and product_photo and product_desc:
                        if len(state['products']) < 18:
                            photo_b64 = base64.b64encode(product_photo.getvalue()).decode()
                            state['products'].append({'name': product_name, 'photo_b64': photo_b64, 'desc': product_desc})
                            st.success(f"Produto '{product_name}' adicionado!")
                        else:
                            st.warning("Limite de 18 produtos atingido.")
                
                if state['products']:
                    st.write("**Produtos Adicionados:**")
                    for i, prod in enumerate(state['products']):
                        c1, c2 = st.columns([3, 1])
                        c1.write(f"_{prod['name']}_")
                        if c2.button("Remover", key=f"del_{i}", use_container_width=True):
                            state['products'].pop(i)
                            st.rerun()

            with st.expander("5. Rodapé"):
                state['footer_text'] = st.text_input("Texto do Rodapé", value=state['footer_text'], key="constr_footer")
        
        # --- COLUNA 2: Pré-visualização e Download ---
        with col2:
            st.subheader("Pré-visualização da Página 📄")

            color_map = {
                'Azul Moderno': {'primary': (37, 99, 235), 'secondary': (219, 234, 254), 'text': (30, 64, 175), 'bg': '#eff6ff'},
                'Verde Crescimento': {'primary': (22, 163, 74), 'secondary': (220, 252, 231), 'text': (20, 83, 45), 'bg': '#f0fdf4'},
                'Roxo Inovação': {'primary': (124, 58, 237), 'secondary': (243, 232, 255), 'text': (88, 28, 135), 'bg': '#faf5ff'},
                'Cinza Corporativo': {'primary': (71, 85, 105), 'secondary': (226, 232, 240), 'text': (30, 41, 59), 'bg': '#f8fafc'},
            }
            font_family = state['theme_font']
            colors = color_map[state['theme_color']]

            # Montando o HTML para o st.markdown (apenas para visualização)
            logo_html = f"<img src='data:image/png;base64,{state['logo_b64']}' style='max-height: 60px; margin-bottom: 1rem;'>" if state['logo_b64'] else ""
            products_html = ""
            if state['products']:
                for prod in state['products'][:6]: # Mostra apenas os primeiros 6 na preview
                    products_html += f"""<div style="background-color: {colors['bg']}; border-left: 4px solid rgb{colors['primary']}; border-radius: 8px; padding: 1rem; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                        <img src="data:image/png;base64,{prod['photo_b64']}" style="width: 100%; height: 120px; object-fit: cover; border-radius: 4px; margin-bottom: 0.5rem;">
                        <h4 style="font-weight: bold; color: rgb{colors['text']}; margin: 0 0 0.5rem 0; font-size:1em;">{prod['name']}</h4><p style="font-size: 0.8rem; color: #4a5568;">{prod['desc']}</p></div>"""
            else:
                products_html = "<p style='text-align: center; color: #9ca3af; grid-column: 1 / -1;'>Seus produtos aparecerão aqui.</p>"
            
            with st.container(border=True):
                st.markdown(f"""
                    <div style="font-family: {font_family}, sans-serif;">
                    <header style="background-color: rgb{colors['primary']}; color: white; text-align: center; padding: 1.5rem;">{logo_html}<h2 style="font-size: 1.5rem; font-weight: bold; margin: 0;">{state['header_pitch']}</h2></header>
                    <main style="padding: 1.5rem;"><div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem;">{products_html}</div></main>
                    <footer style="background-color: rgb{colors['secondary']}; text-align: center; padding: 0.75rem; font-size: 0.7rem; color: #374151; border-top: 2px solid rgb{colors['primary']};">{state['footer_text']}</footer>
                    </div>""", unsafe_allow_html=True)
            
            # --- Geração e Download do PDF ---
            class PDF(FPDF):
                def __init__(self, state, colors, font_family):
                    super().__init__()
                    self.state = state
                    self.colors = colors
                    self.font_family = font_family
                    try: # Adiciona fontes. Garanta que os arquivos .ttf estão na pasta 'assets'
                        self.add_font(font_family, '', get_asset_path(f"{font_family}.ttf"), uni=True)
                        self.add_font(font_family, 'B', get_asset_path(f"{font_family}-Bold.ttf"), uni=True)
                    except RuntimeError:
                        st.warning(f"Fonte {font_family} não encontrada. Usando Arial."); self.font_family = "Arial"
                        
                def header(self):
                    self.set_fill_color(*self.colors['primary']); self.rect(0, 0, 210, 40, 'F')
                    if self.state['logo_b64']:
                        self.image(io.BytesIO(base64.b64decode(self.state['logo_b64'])), x=10, y=8, h=15, type='PNG')
                    self.set_font(self.font_family, 'B', 16); self.set_text_color(255, 255, 255)
                    self.cell(0, 50, self.state['header_pitch'], 0, 1, 'C')

                def footer(self):
                    self.set_y(-15); self.set_fill_color(*self.colors['secondary']); self.rect(0, 282, 210, 15, 'F')
                    self.set_font(self.font_family, '', 8); self.set_text_color(55, 65, 81)
                    self.cell(0, 10, self.state['footer_text'], 0, 0, 'C')

                def product_grid(self):
                    self.set_y(50)
                    col_width = 60; row_height = 65; x_margin = 15; y_margin = 10
                    for i, prod in enumerate(self.state['products']):
                        if i > 0 and i % 3 == 0: self.ln(row_height + y_margin) # Nova linha
                        x_pos = x_margin + (i % 3) * (col_width + 5)
                        y_pos = self.get_y()
                        self.image(io.BytesIO(base64.b64decode(prod['photo_b64'])), x=x_pos, y=y_pos, w=col_width, h=35, type='PNG')
                        self.set_xy(x_pos, y_pos + 37)
                        self.set_font(self.font_family, 'B', 12); self.set_text_color(*self.colors['text'])
                        self.multi_cell(col_width, 5, prod['name'])
                        self.set_xy(x_pos, self.get_y())
                        self.set_font(self.font_family, '', 10); self.set_text_color(74, 85, 104)
                        self.multi_cell(col_width, 5, prod['desc'])
                        self.set_y(y_pos)

            pdf = PDF(state, colors, font_family)
            pdf.add_page()
            pdf.product_grid()
            
            # Adiciona mais páginas se necessário
            if len(state['products']) > 6:
                pdf.add_page(); pdf.product_grid()
            if len(state['products']) > 12:
                pdf.add_page(); pdf.product_grid()
                
            pdf_output = pdf.output(dest='S').encode('latin-1')
            
            st.download_button(
                label="📥 Baixar Página em PDF", data=pdf_output, file_name="minha_pagina_de_vendas.pdf",
                mime="application/pdf", use_container_width=True
            )


    # Onboarding
    def exibir_onboarding_calibracao(self): st.title("Calibração da Empresa...")
    def exibir_onboarding_trainer(self): st.title("Personalização da Experiência...")
    def exibir_tour_guiado(self): st.title("Tour Guiado...")

# ==============================================================================
# 6. FUNÇÕES DA INTERFACE DE ENTRADA (VERSÃO ESTÁVEL)
# ==============================================================================

def exibir_pagina_de_entrada():
    """Renderiza a capa de abertura com 2 opções: Cliente ou Não Cliente."""
    try:
        logo_base64 = convert_image_to_base64('max-ia-lgo.fundo.transparente.png')
        background_image_url = "https://images.pexels.com/photos/3184418/pexels-photo-3184418.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=1"
        st.markdown(f"""
            <style>
            .stApp {{ background-image: linear-gradient(rgba(0,0,0,0.6), rgba(0,0,0,0.6)), url("{background_image_url}"); background-size: cover; background-position: center; }}
            .stApp > header, .stSidebar {{ background-color: transparent !important; }}
            .main-container {{ display: flex; flex-direction: column; justify-content: flex-end; align-items: center; height: 90vh; padding-bottom: 5vh; }}
            .logo-container {{ position: absolute; top: 2rem; left: 2rem; }}
            [data-testid="stSidebar"] {{ display: none; }}
            </style>""", unsafe_allow_html=True)
        if logo_base64:
            st.markdown(f"<div class='logo-container'><img src='data:image/png;base64,{logo_base64}' width='150'></div>", unsafe_allow_html=True)
    except Exception as e:
        print(f"Alerta: Não foi possível renderizar a página de entrada com imagens. Erro: {e}")

    with st.container():
        st.markdown("<div class='main-container'>", unsafe_allow_html=True)
        _ , col, _ = st.columns([1, 2.5, 1])
        with col:
            if st.button("Já sou cliente", use_container_width=True):
                st.session_state['show_login_form'] = True
                st.rerun()
            if st.button("Ainda não sou cliente", type="secondary", use_container_width=True):
                st.html(f"<script>window.open('{SALES_PAGE_URL}', '_blank')</script>")
            st.caption("<p style='text-align: center; color: white;'>Ao continuar, você aceita nossos Termos e condições.</p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)


def exibir_formularios_de_acesso():
    """Renderiza os formulários de login e registro no corpo da página."""
    st.markdown("""<style>[data-testid="stSidebar"] { display: none; }</style>""", unsafe_allow_html=True)
    _ , col, _ = st.columns([1, 1.5, 1])
    with col:
        try:
            logo_path = get_asset_path('max-ia-lgo.fundo.transparente.png')
            if os.path.exists(logo_path):
                st.image(logo_path, width=150)
        except Exception:
            st.title("Max IA Empresarial")
        
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
                        st.session_state['show_login_form'] = False
                        st.rerun()
                    except Exception:
                        st.error("Email ou senha inválidos.")
        with tab_register:
            with st.form("register_form_main"):
                reg_email = st.text_input("Seu melhor e-mail", key="reg_email")
                reg_password = st.text_input("Crie uma senha forte", type="password", key="reg_pass")
                if st.form_submit_button("Registrar Conta", use_container_width=True):
                    if reg_email and len(reg_password) >= 6:
                        try:
                            new_user = pb_auth_client.create_user_with_email_and_password(reg_email, reg_password)
                            user_data = { "email": reg_email, "registration_date": firebase_admin_firestore.SERVER_TIMESTAMP, "access_level": 2, "company_id": None, "analogy_domain": None }
                            firestore_db.collection(USER_COLLECTION).document(new_user['localId']).set(user_data)
                            st.success("Conta criada! Volte para a aba 'Login' para entrar.")
                        except Exception:
                            st.error("Este e-mail já está em uso ou ocorreu um erro.")
                    else:
                        st.warning("Preencha todos os campos corretamente.")

# ==============================================================================
# 7. ESTRUTURA PRINCIPAL E EXECUÇÃO DO APP (VERSÃO ESTÁVEL)
# ==============================================================================
def main():
    if not all([pb_auth_client, firestore_db]):
        st.error("Falha crítica na inicialização dos serviços."); st.stop()

    user_is_authenticated, user_uid, user_email = get_current_user_status(pb_auth_client)

    if user_is_authenticated:
        # --- USUÁRIO LOGADO: FLUXO PRINCIPAL DO APP ---
        try:
            logo_path = get_asset_path('max-ia-lgo.fundo.transparente.png')
            if os.path.exists(logo_path):
                st.sidebar.image(logo_path, width=100)
        except Exception as e:
            print(f"Alerta: Não foi possível carregar a logo da sidebar. Erro: {e}")

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
        
        # --- LÓGICA DE ACESSO POR NÍVEL ---
        opcoes_menu_completo = {
            "👋 Bem-vindo": agente.exibir_painel_boas_vindas,
            "🏢 Central de Comando": agente.exibir_central_de_comando,
            "💰 MaxFinanceiro": agente.exibir_max_financeiro,
            "📈 Central do Cliente 360°": agente.exibir_central_cliente,
            "🚀 MaxMarketing Total": agente.exibir_max_marketing_total,
            "🎓 MaxTrainer IA": agente.exibir_max_trainer_ia,
            "🏗️ MaxConstrutor": agente.exibir_max_construtor,
        }
        
        access_level = user_data.get('access_level', 2)
        opcoes_permitidas_nomes = []

        if access_level == 1:
            opcoes_permitidas_nomes = list(opcoes_menu_completo.keys())
        else:
            opcoes_permitidas_nomes = ["👋 Bem-vindo", "🎓 MaxTrainer IA"]
            if access_level == 2: opcoes_permitidas_nomes.append("📈 Central do Cliente 360°")
            elif access_level == 3: opcoes_permitidas_nomes.append("🚀 MaxMarketing Total")
            elif access_level == 4: opcoes_permitidas_nomes.append("🏗️ MaxConstrutor")
            elif access_level == 5: opcoes_permitidas_nomes.append("💰 MaxFinanceiro")
            elif access_level == 6: opcoes_permitidas_nomes.append("🏢 Central de Comando")
        
        opcoes_menu_filtrado = {nome: funcao for nome, funcao in opcoes_menu_completo.items() if nome in opcoes_permitidas_nomes}

        selecao_label = st.sidebar.radio("Max Agentes IA:", list(opcoes_menu_filtrado.keys()), key=f"{APP_KEY_SUFFIX}_menu")
        if selecao_label in opcoes_menu_filtrado:
            opcoes_menu_filtrado[selecao_label]()

    else:
        # --- USUÁRIO NÃO LOGADO: FLUXO DE ENTRADA SIMPLES ---
        if st.session_state.get('show_login_form', False):
            exibir_formularios_de_acesso()
        else:
            exibir_pagina_de_entrada()

if __name__ == "__main__":
    main()
