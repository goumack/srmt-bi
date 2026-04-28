# SRMT Business Intelligence - Production Dockerfile
# Optimisé pour OpenShift (non-root, port 8080, multi-stage)

# --- Étape 1: Builder (compilation des dépendances) ---
FROM python:3.11-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY requirements-prod.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements-prod.txt

# --- Étape 2: Image finale légère ---
FROM python:3.11-slim

LABEL maintainer="SRMT BI Team" \
      description="SRMT Business Intelligence - Plateforme d'Analyse Fiscale" \
      version="2.0"

# Copier les dépendances compilées depuis le builder
COPY --from=builder /install /usr/local

# Utilisateur non-root (obligatoire sur OpenShift)
RUN groupadd -r srmt && useradd -r -g srmt -d /app -s /sbin/nologin srmt

WORKDIR /app

# Copier uniquement les fichiers nécessaires (pas les backups, .venv, etc.)
COPY srmt_production_ready.py .
COPY gunicorn_config.py .
COPY ai_learning_system.py .
COPY decision_presenter.py .
COPY query_optimizer.py .
COPY templates/ templates/
COPY srmt_data_2020_2025.parquet .

# Répertoires avec les bons droits
# OpenShift exécute souvent avec un UID arbitraire (groupe 0)
RUN mkdir -p /app/logs /app/cache && \
    chown -R srmt:0 /app && \
    chmod -R g=u /app

# Variables d'environnement
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080 \
    HOST=0.0.0.0 \
    PRODUCTION=true \
    DATA_FILE=./srmt_data_2020_2025.parquet \
    MAX_WORKERS=2 \
    REQUEST_TIMEOUT=120 \
    LOG_LEVEL=INFO

# Port OpenShift standard
EXPOSE 8080

# Passer à l'utilisateur non-root
USER srmt

# Health check adapté au temps de chargement des données (~30s)
HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/api/health')" || exit 1

# Démarrage Gunicorn (gthread au lieu de gevent pour compatibilité)
CMD ["gunicorn", \
     "--bind", "0.0.0.0:8080", \
     "--workers", "2", \
     "--worker-class", "gthread", \
     "--threads", "4", \
     "--timeout", "120", \
     "--preload", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "srmt_production_ready:create_production_app()"]
