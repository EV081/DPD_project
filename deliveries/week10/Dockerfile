FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

WORKDIR /app

COPY requirements-pipeline.txt .
RUN pip install -r requirements-pipeline.txt

COPY code/pipeline ./pipeline
COPY code/storage ./storage
COPY code/export ./export
COPY code/tests ./tests
COPY code/entrypoint.sh ./entrypoint.sh
RUN chmod +x entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]
CMD ["full"]
