# Identico al patron de unlu-ia-infra-cloud/model/Dockerfile:
# Entrena el modelo propio en BUILD TIME y sella el prompt adentro de la imagen.
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY sample_500.csv train.py serve.py config.py ./
COPY domain/ ./domain/
COPY adapters/ ./adapters/
COPY api/ ./api/
COPY templates/ ./templates/
COPY prompts/ ./prompts/
RUN python train.py

ARG MODEL_VERSION=v1
ENV MODEL_PATH=/app/model.joblib \
    PROMPT_PATH=/app/prompts/system_prompt.txt \
    PORT=8081 \
    MODEL_VERSION=${MODEL_VERSION}

EXPOSE 8081

CMD ["python", "serve.py"]
