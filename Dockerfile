# Atalaya - imagen en tres etapas:
#   base : lo comun (Python, dependencias, codigo, usuario sin privilegios).
#   kit  : kit autoalojado para una organizacion (modo gmail; docs/INSTALACION.md, ADR 0012).
#   demo : despliegue publico (SOLO modo demo; ADR 0004). Es la ULTIMA etapa a proposito:
#          `docker build .` y Render construyen la ultima, asi que su comportamiento no cambia.
# Para el kit: `docker build --target kit .` (docker-compose.yml ya lo hace).

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv

# Parches de seguridad del sistema base: la imagen python:3.12-slim puede traer paquetes de Debian
# con una correccion ya publicada (el escaneo de Trivy del CI lo detecto con zlib1g).
# hadolint ignore=DL3008,DL3009
RUN apt-get update     && apt-get upgrade -y --no-install-recommends     && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

# Solo el codigo de la app (el resto queda fuera por .dockerignore: .env, .git, data/, etc.)
COPY app ./app

# Usuario sin privilegios
RUN useradd --system --no-create-home --uid 10001 atalaya

# La plataforma (Render/Railway) define PORT; 8000 por defecto en local.
ENV PORT=8000
EXPOSE 8000

# Comprobacion de salud de la propia imagen (usa solo la biblioteca estandar).
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3   CMD ["python", "-c", "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/health' % os.environ.get('PORT','8000'), timeout=4)"]


# ---------------------------------------------------------------------------------------------
# Kit autoalojado: modo gmail con las claves y la aplicacion de Google de la propia organizacion.
FROM base AS kit

# Carpeta del volumen de datos: la base SQLite vive aqui. Con un volumen con nombre, Docker
# copia este duenio (uid 10001) la primera vez. No uses una carpeta del anfitrion sin ajustar
# el duenio (ver docs/INSTALACION.md, solucion de problemas).
RUN mkdir -p /srv/data && chown atalaya /srv/data
VOLUME ["/srv/data"]
# hadolint ignore=DL3066
USER atalaya

ENV ATALAYA_MODE=gmail \
    ATALAYA_DB_PATH=/srv/data/atalaya.db

# 1) `app.kit_preflight` se niega a arrancar (mensaje en espanol) si falta una variable obligatoria.
# 2) La URI de redireccion de Google se deriva de ATALAYA_BASE_URL (puede fijarse con GOOGLE_REDIRECT_URI).
# 3) --no-proxy-headers: uvicorn no se fia de X-Forwarded-*; el limite de intentos del panel usa
#    ATALAYA_TRUST_PROXY=1 (ultima entrada de X-Forwarded-For, la que agrega Caddy). Ver docs/INSTALACION.md.
CMD ["sh", "-c", "python -m app.kit_preflight && export GOOGLE_REDIRECT_URI=\"${GOOGLE_REDIRECT_URI:-${ATALAYA_BASE_URL%/}/auth/google/callback}\" && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --no-proxy-headers --no-server-header"]


# ---------------------------------------------------------------------------------------------
# Demo publica (Render/Railway). Debe seguir siendo la ULTIMA etapa.
FROM base AS demo

# hadolint ignore=DL3066
USER atalaya

# ATALAYA_MODE=demo se fuerza al arrancar: aunque la plataforma tenga otro valor, el
# despliegue publico nunca usa modo gmail.
# Direccion del visitante: NO se confia en las cabeceras de proxy de uvicorn (con la lista de IP de confianza en comodin, uvicorn
# creia la PRIMERA entrada de X-Forwarded-For, que escribe el cliente, y los limites se saltaban
# con una cabecera falsa). La app lee la entrada que agrega nuestro proxy (la ultima); si hay mas
# de un salto propio delante (por ejemplo una CDN), subir ATALAYA_TRUSTED_HOPS. Ver ADR 0007.
ENV ATALAYA_TRUSTED_HOPS=1
CMD ["sh", "-c", "ATALAYA_MODE=demo exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --no-proxy-headers --no-server-header"]
