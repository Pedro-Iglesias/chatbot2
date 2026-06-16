FROM python:3.11-slim

# Dependências do sistema para leitura de PDF (pypdf / pdfplumber)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Usuário não-root (hardening): evita rodar o container como root.
# uid 1000 + chown do /app para funcionar também com o bind mount do
# docker-compose (- .:/app) sem erro de permissão.
RUN useradd --create-home --uid 1000 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
