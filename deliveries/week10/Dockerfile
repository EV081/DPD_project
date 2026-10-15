FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

WORKDIR /app

# LightGBM necesita OpenMP (libgomp); python:slim no lo trae y sin el cae a media_4sem en silencio
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
 && rm -rf /var/lib/apt/lists/*

COPY requirements-pipeline.txt .
RUN pip install -r requirements-pipeline.txt

COPY code/pipeline ./pipeline
COPY code/storage ./storage
COPY code/export ./export
COPY code/tests ./tests
# los tests de georreferenciacion (test_google, test_revision) importan estos modulos
COPY code/scripts/03_georef ./scripts/03_georef
# Inferencia del batch `predict`: MODEL_DIR.parents[1]/"models" -> /models (ver inferencia.py)
COPY code/model/*.py ./model/
COPY models /models
COPY code/entrypoint.sh ./entrypoint.sh
RUN chmod +x entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]
CMD ["full"]
