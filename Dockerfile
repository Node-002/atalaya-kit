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

# Comprobacion de salud de la propia imagen (usa solo la biblioteca estandar).
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3   CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/health' % os.environ.get('PORT','8000'), timeout=4)"

# ATALAYA_MODE=demo se fuerza al arrancar: aunque la plataforma tenga otro valor, el
# despliegue publico nunca usa modo gmail.
# Direccion del visitante: NO se confia en las cabeceras de proxy de uvicorn (con la lista de IP de confianza en comodin, uvicorn
# creia la PRIMERA entrada de X-Forwarded-For, que escribe el cliente, y los limites se saltaban
# con una cabecera falsa). La app lee la entrada que agrega nuestro proxy (la ultima); si hay mas
# de un salto propio delante (por ejemplo una CDN), subir ATALAYA_TRUSTED_HOPS. Ver ADR 0007.
ENV ATALAYA_TRUSTED_HOPS=1
CMD ["sh", "-c", "ATALAYA_MODE=demo exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --no-proxy-headers --no-server-header"]
