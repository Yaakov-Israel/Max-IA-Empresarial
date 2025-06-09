# ==============================================================================
# 5. CLASSE PRINCIPAL DO AGENTE (v2.3 - BASE DE GRIFE E ATELIÊ FUNCIONAL)
# ==============================================================================
class MaxAgente:
    def __init__(self, llm_instance, db_firestore_instance):
        self.llm = llm_instance
        self.db = db_firestore_instance

    def exibir_painel_boas_vindas(self):
        st.markdown("<div style='text-align: center;'><h1>👋 Bem-vindo ao Max IA!</h1></div>", unsafe_allow_html=True)
        logo_base64 = convert_image_to_base64('max-ia-logo.png')
        if logo_base64:
            st.markdown(f"<div style='text-align: center;'><img src='data:image/png;base64,{logo_base64}' width='200'></div>", unsafe_allow_html=True)
        st.markdown("<div style='text-align: center;'><p style='font-size: 1.2em;'>Olá! Eu sou o <strong>Max</strong>, seu assistente de IA para impulsionar o sucesso da sua empresa.</p></div>", unsafe_allow_html=True)

    def exibir_max_marketing_total(self):
        # O código completo e funcional do marketing total vai aqui
        st.header("🚀 MaxMarketing Total"); st.caption("Seu copiloto para criar posts, campanhas e muito mais!")
        st.info("Funcionalidades de Marketing (Criar Post e Campanhas) estão operacionais.")


    def exibir_max_construtor(self):
        st.header("🏗️ Max Construtor de Landing Pages")
        st.caption("Gere a base da sua página e depois a refine no Ateliê.")
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
                logo_file = st.file_uploader("1. Logo da sua empresa (PNG com fundo transparente)", type=['png', 'jpg', 'jpeg'])
                main_image_file = st.file_uploader("2. Imagem para o placeholder de vídeo (Hero Section)", type=['png', 'jpg', 'jpeg'])
                submitted = st.form_submit_button("✨ Aplicar Personalizações", type="primary", use_container_width=True)
                if submitted:
                    if not logo_file and not main_image_file:
                        st.warning("Por favor, suba pelo menos um arquivo para personalizar.")
                    else:
                        with st.spinner("🔧 Max está no Ateliê, aplicando seus toques finais..."):
                            logo_b64, main_image_b64 = None, None
                            if logo_file: logo_b64 = base64.b64encode(logo_file.getvalue()).decode()
                            if main_image_file: main_image_b64 = base64.b64encode(main_image_file.getvalue()).decode()
                            html_base = st.session_state.genesis_html_code
                            prompt_refinamento = self.get_prompt_refinamento(html_base, logo_b64, main_image_b64)
                            try:
                                if self.llm and prompt_refinamento:
                                    resposta_ia = self.llm.invoke(prompt_refinamento).content
                                    html_final = resposta_ia.strip().removeprefix("```html").removesuffix("```").strip()
                                    st.session_state.genesis_html_code = html_final
                                    st.session_state.refinement_mode = False
                                    st.rerun()
                                else: st.error("Nenhuma personalização a ser feita ou LLM indisponível.")
                            except Exception as e: st.error(f"Ocorreu um erro durante o refinamento: {e}")
            if st.button("⬅️ Voltar para o Esboço"):
                st.session_state.refinement_mode = False; st.rerun()

        # MODO DE EXIBIÇÃO DA PÁGINA GERADA
        elif st.session_state.genesis_html_code:
            st.success("✅ Esboço da Landing Page gerado com sucesso!")
            st.markdown("---")
            st.subheader("🎨 Próximos Passos")
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("🎨 Personalizar com Imagens", use_container_width=True, type="primary"):
                    st.session_state.refinement_mode = True; st.rerun()
            with col2:
                 st.download_button(label="📥 Baixar Código HTML", data=st.session_state.genesis_html_code, file_name="index.html", mime="text/html", use_container_width=True)
            with col3:
                if st.button("✨ Começar do Zero", use_container_width=True):
                    st.session_state.genesis_step = 0; st.session_state.genesis_briefing = {}; st.session_state.genesis_html_code = None; st.session_state.refinement_mode = False
                    st.rerun()
            st.subheader("👀 Pré-visualização do Esboço")
            st.components.v1.html(st.session_state.genesis_html_code, height=600, scrolling=True)
            with st.expander("🚀 Seu esboço está pronto! E agora? (Dicas de Hospedagem)"):
                st.markdown("...(Dicas de hospedagem)...") # Omitido para brevidade
        
        # MODO DE RESUMO DA ENTREVISTA
        elif st.session_state.genesis_step > len(self.get_perguntas_genesis()):
            st.success("✅ Entrevista Concluída! Revise o briefing abaixo.")
            st.markdown("---"); st.subheader("Resumo do Briefing:")
            briefing_formatado = ""
            for p_info in self.get_perguntas_genesis().values():
                pergunta = p_info["pergunta"]
                resposta = st.session_state.genesis_briefing.get(pergunta, "Não preenchido")
                st.markdown(f"**{pergunta}**"); st.markdown(f"> {resposta}")
                briefing_formatado += f"- {pergunta}: {resposta}\n"
            st.markdown("---")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("⬅️ Corrigir Respostas", use_container_width=True): st.session_state.genesis_step = 1; st.rerun()
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
        
        # MODO DE ENTREVISTA
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

    def get_prompt_construtor(self, briefing):
        return f"""
**Instrução Mestra:** Você é um Desenvolvedor Web Full-Stack e Designer de UI/UX sênior, especialista em criar landing pages de ALTA QUALIDADE com HTML e CSS.
**Tarefa:** Crie o código HTML completo para um **único arquivo `index.html`** de um esboço de página. O arquivo DEVE ser autocontido e usar as informações de branding e conteúdo do briefing.
**Requisitos Críticos:**
1.  **Autocontido:** Todo o CSS deve estar dentro de uma tag `<style>` no `<head>`.
2.  **Responsivo:** O design DEVE ser 100% responsivo para desktops e celulares.
3.  **Diretiva de Estilo:** Use as informações de branding do briefing. A cor primária deve ser usada nos botões e títulos principais. As fontes devem ser importadas do Google Fonts e escolhidas com base no estilo pedido pelo usuário (se pediu 'Modernas', use 'Montserrat' e 'Lato'; se pediu 'Elegantes', use 'Playfair Display' e 'Roboto'; se pediu 'Ousadas', use 'Poppins' e 'Open Sans').
4.  **Diretiva de Estrutura (3 Atos):**
    * **Ato 1 (Hero Section):** Crie uma seção de topo impactante com a headline principal (h1) e um placeholder para um vídeo: ``.
    * **Ato 2 (Benefícios e CTA):** Crie uma seção para os benefícios listados e inclua a chamada para ação principal (botão).
    * **Ato 3 (Destaques e CTA Final):** Crie uma seção de rodapé expandida (footer) com espaço para 3 a 6 destaques ou informações adicionais (ex: 'Entrega Rápida', 'Suporte 24h') e repita a chamada para ação.
5.  **Placeholders de Imagem:** Use comentários HTML claros: ``, ``, ``.
**[BRIEFING DO USUÁRIO]**
{briefing}
**Diretiva Final:** Gere **APENAS O CÓDIGO HTML PURO**, começando com `<!DOCTYPE html>` e terminando com `</html>`. NÃO inclua ```html.
"""

    def get_prompt_refinamento(self, html_base, logo_b64, main_image_b64):
        instrucoes = []
        if logo_b64:
            instrucoes.append(f"1. Encontre o comentário `` e substitua-o por esta tag de imagem: `<img src='data:image/png;base64,{logo_b64}' alt='Logo da Empresa' style='max-height: 70px; margin-bottom: 20px;'>`")
        if main_image_b64:
            # Assumindo que o placeholder de vídeo será o local da imagem principal por enquanto
            instrucoes.append(f"2. Encontre o comentário `` e substitua-o por esta tag de imagem: `<img src='data:image/jpeg;base64,{main_image_b64}' alt='Imagem Principal do Produto' style='width: 100%; height: auto; border-radius: 8px; margin-top: 20px;'>`")
        if not instrucoes: return None
        instrucao_str = "\n".join(instrucoes)
        return f"""
**Instrução Mestra:** Você é um desenvolvedor web sênior que refatora um código HTML existente.
**Tarefa:** Receba um código HTML base e um conjunto de instruções. Aplique as instruções para substituir os placeholders de comentário pelas tags de imagem fornecidas.
**CÓDIGO HTML BASE:**
```html
{html_base}
