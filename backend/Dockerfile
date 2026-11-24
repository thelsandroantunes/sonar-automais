FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends postgresql-client \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ /app/backend/
COPY dados-referencia/ /app/dados-referencia/
WORKDIR /app/backend
CMD ["python", "-m", "coleta.coletar_leiloes_pncp"]
