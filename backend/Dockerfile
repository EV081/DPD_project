FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# LightGBM necesita OpenMP (libgomp); python:slim no lo trae
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 5000
# Render define PORT; en compose queda 5000. --timeout alto: el primer pedido carga los modelos.
# WEB_CONCURRENCY = nº de workers; cada uno carga su copia de los modelos y del grafo del Eje 2 (usa 1 en servidores de 512 MB).
CMD ["sh", "-c", "gunicorn app:app --bind 0.0.0.0:${PORT:-5000} --workers ${WEB_CONCURRENCY:-2} --timeout 120"]
