# Identico al patron de unlu-ia-infra-cloud/model/Dockerfile:
# Entrena el modelo propio en BUILD TIME y sella el prompt adentro de la imagen.
FROM python:3.12-slim

WORKDIR /app

COPY model/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY data/sample_1000.csv data/sample_1000.csv
COPY model/train.py model/serve.py model/config.py ./
COPY model/domain/ ./domain/
COPY model/adapters/ ./adapters/
COPY model/api/ ./api/
COPY model/templates/ ./templates/
COPY model/prompts/ ./prompts/
RUN python train.py

ARG MODEL_VERSION=v1
ENV MODEL_PATH=/app/model.joblib \
    PROMPT_PATH=/app/prompts/system_prompt.txt \
    PORT=8081 \
    MODEL_VERSION=${MODEL_VERSION}

EXPOSE 8081

CMD ["python", "serve.py"]
