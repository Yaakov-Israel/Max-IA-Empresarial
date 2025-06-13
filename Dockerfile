# Etapa 1: Usar uma imagem base oficial do Python. A versão "slim" é leve e boa para produção.
FROM python:3.11-slim

# Etapa 2: Definir o diretório de trabalho dentro do contêiner.
# Todos os comandos a seguir serão executados a partir desta pasta.
WORKDIR /app

# Etapa 3: Instalar dependências de sistema (se houver).
# O arquivo packages.txt do Streamlit Cloud serve para isso. Este comando lê cada
# linha do arquivo e instala o pacote correspondente.
COPY packages.txt .
RUN apt-get update && xargs -a packages.txt apt-get install -y --no-install-recommends && apt-get clean && rm -rf /var/lib/apt/lists/*

# Etapa 4: Copiar e instalar as dependências do Python.
# Copiamos o requirements.txt primeiro para aproveitar o cache do Docker.
# Se o arquivo não mudar, o Docker não reinstalará as dependências toda vez.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Etapa 5: Copiar TODO o resto do código do seu projeto para o contêiner.
# Isso inclui seu streamlit_app.py e as pastas 'assets' e 'prompts'.
# O primeiro "." significa "tudo na pasta atual do seu computador".
# O segundo "." significa "para o diretório de trabalho atual no contêiner (/app)".
COPY . .

# Etapa 6: Expor a porta que o Streamlit usa.
# Isso informa ao Docker que o contêiner escuta nesta porta.
EXPOSE 8501

# Etapa 7: Adicionar um "Health Check".
# O Google Cloud Run usa isso para saber se sua aplicação está rodando e saudável.
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Etapa 8: O comando para iniciar seu aplicativo quando o contêiner rodar.
# Usamos "server.headless=true" para rodar corretamente em um ambiente de nuvem.
# "server.address=0.0.0.0" permite que o serviço seja acessado de fora do contêiner.
CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
