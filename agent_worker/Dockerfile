FROM python:3.12-slim

  WORKDIR /app

  # Install requirements first (cached layer)
  COPY agent_worker/requirements.txt /app/requirements.txt
  RUN pip install --no-cache-dir -r requirements.txt

  # Pre-download ML models during build (baked into image)
  # This avoids ~30s cold start on first request
  RUN python -c "\
  from sentence_transformers import SentenceTransformer; \
  SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')"

  RUN python -c "\
  from transformers import AutoTokenizer, AutoModelForSequenceClassification; \
  AutoTokenizer.from_pretrained('google/muril-base-cased'); \
  AutoModelForSequenceClassification.from_pretrained('google/muril-base-cased')"

  # Copy application code
  COPY shared/ /app/shared/
  COPY agent_worker/ /app/agent_worker/
  COPY models/ /app/models/
  COPY pyproject.toml /app/pyproject.toml
  RUN pip install -e .

  # Default to text topic — override via env var
  ENV KAFKA_TOPIC=farmer-messages-text

  CMD ["python", "-m", "agent_worker.worker"]