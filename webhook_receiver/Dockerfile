FROM python:3.12-slim

WORKDIR /app

COPY webhook_receiver/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ /app/shared/
COPY webhook_receiver/ /app/webhook_receiver/
COPY pyproject.toml /app/pyproject.toml
RUN pip install -e .

CMD ["uvicorn", "webhook_receiver.app:app", "--host", "0.0.0.0", "--port", "8080"]
