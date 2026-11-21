# Atalaya - imagen para el despliegue publico (SOLO modo demo).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv

COPY requirements.txt .
RUN pip install -r requirements.txt

# Solo el codigo de la app (el resto queda fuera por .dockerignore: .env, .git, data/, etc.)
COPY app ./app

# Usuario sin privilegios
RUN useradd --system --no-create-home --uid 10001 atalaya
USER atalaya

# La plataforma (Render/Railway) define PORT; 8000 por defecto en local.
ENV PORT=8000
EXPOSE 8000

# ATALAYA_MODE=demo se fuerza al arrancar: aunque la plataforma tenga otro valor, el
# despliegue publico nunca usa modo gmail. --proxy-headers para HTTPS detras del proxy.
CMD ["sh", "-c", "ATALAYA_MODE=demo exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
