# ============================================
# AI Aura & Personality Reader - Dockerfile
# ============================================
# Multi-service Docker image using SERVICE env var
# to select which component to run.
#
# Services: fastapi, consumer, dashboard
# ============================================

FROM python:3.11-slim

# ── System dependencies ──
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        librdkafka-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

# ── Working directory ──
WORKDIR /app

# ── Install Python dependencies ──
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Download NLTK data at build time ──
RUN python -c "\
import nltk; \
nltk.download('punkt_tab', quiet=True); \
nltk.download('averaged_perceptron_tagger_eng', quiet=True); \
nltk.download('stopwords', quiet=True); \
nltk.download('wordnet', quiet=True)"

# ── Install python-multipart explicitly ──
RUN pip install --no-cache-dir python-multipart==0.0.19

# ── Copy application source ──
RUN echo "force_copy_v1"
COPY . .


# ── Create directories ──
RUN mkdir -p /app/templates /app/static /app/screenshots

# ── Environment defaults ──
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV SERVICE=fastapi

# ── Health check ──
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/ || curl -f http://localhost:8501/_stcore/health || exit 1

# ── Entrypoint script ──
# Uses SERVICE env var to determine which component to start
COPY <<'EOF' /app/entrypoint.sh
#!/bin/bash
set -e

echo "╔══════════════════════════════════════════════╗"
echo "║   🔮 AI Aura & Personality Reader            ║"
echo "║   Starting service: $SERVICE                 ║"
echo "╚══════════════════════════════════════════════╝"

case "$SERVICE" in
    fastapi)
        echo "🚀 Starting FastAPI server on port ${PORT:-8000}..."
        exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --log-level info
        ;;
    consumer)
        echo "📥 Starting Kafka Consumer service..."
        exec python consumer.py
        ;;
    dashboard)
        echo "🖥️  Starting Streamlit Dashboard on port 8501..."
        exec streamlit run dashboard.py \
            --server.port=8501 \
            --server.address=0.0.0.0 \
            --server.headless=true \
            --browser.gatherUsageStats=false \
            --theme.base=dark \
            --theme.primaryColor="#9B59B6" \
            --theme.backgroundColor="#0a0a0f" \
            --theme.secondaryBackgroundColor="#1a1a2e" \
            --theme.textColor="#e0e0e0"
        ;;
    *)
        echo "❌ Unknown service: $SERVICE"
        echo "   Valid options: fastapi, consumer, dashboard"
        exit 1
        ;;
esac
EOF

RUN chmod +x /app/entrypoint.sh

# ── Default command ──
ENTRYPOINT ["/bin/bash", "/app/entrypoint.sh"]
