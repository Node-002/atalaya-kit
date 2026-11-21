#!/usr/bin/env bash
# Comprueba la imagen Docker de Atalaya (despliegue publico, SOLO modo demo).
# Uso: check-image.sh <imagen>   (la imagen debe existir ya: docker build -t atalaya:ci .)
set -euo pipefail

IMG="${1:?uso: check-image.sh <imagen>}"
PORT_HOST=8000
BASE="http://127.0.0.1:${PORT_HOST}"
FALLOS=0
CONT=""
CONT2=""

limpiar() {
  for c in "$CONT" "$CONT2"; do
    [ -n "$c" ] && docker rm -f "$c" >/dev/null 2>&1 || true
  done
}
trap limpiar EXIT

ok()   { echo "OK    $1"; }
fallo() { echo "FALLA $1"; FALLOS=$((FALLOS + 1)); }
espera_health() { # $1 = puerto
  for _ in $(seq 1 40); do
    curl -fsS "http://127.0.0.1:$1/health" >/dev/null 2>&1 && return 0
    sleep 1
  done
  return 1
}
codigo() { curl -s -o /dev/null -w '%{http_code}' "$BASE$1"; }

CONT=$(docker run -d -e PORT=8000 -p "${PORT_HOST}:8000" "$IMG")
if ! espera_health "$PORT_HOST"; then
  echo "La imagen no respondio en /health en 40 s. Registro del contenedor:"
  docker logs "$CONT" || true
  exit 1
fi

# 1. /health
SALUD=$(curl -fsS "$BASE/health" | jq -cS .)
[ "$SALUD" = '{"auth":false,"mode":"demo","status":"ok"}' ] \
  && ok "/health = $SALUD" || fallo "/health inesperado: $SALUD"

# 2. Documentacion automatica y login de Google apagados
for ruta in /docs /openapi.json /auth/google/login; do
  C=$(codigo "$ruta")
  [ "$C" = 404 ] && ok "$ruta da 404" || fallo "$ruta dio $C (se esperaba 404)"
done

# 3. Sin cabecera Server
if curl -sI "$BASE/health" | grep -qi '^server:'; then
  fallo "la cabecera Server aparece"
else
  ok "no hay cabecera Server"
fi

# 4. Cookie de sesion de la demo
COOKIE=$(curl -sI "$BASE/api/alerts" | grep -i '^set-cookie: atalaya_demo_sid' || true)
if [ -z "$COOKIE" ]; then
  fallo "no se emitio la cookie atalaya_demo_sid"
elif echo "$COOKIE" | grep -qi 'HttpOnly' && echo "$COOKIE" | grep -qi 'SameSite=Lax'; then
  ok "cookie atalaya_demo_sid con HttpOnly y SameSite=Lax"
else
  fallo "cookie sin HttpOnly/SameSite=Lax"
fi

# 5. Usuario sin privilegios
UID_PROC=$(docker exec "$CONT" id -u)
[ "$UID_PROC" != 0 ] && ok "el proceso corre como uid $UID_PROC (no root)" \
  || fallo "el contenedor corre como root"

# 6. HEALTHCHECK de la imagen
ESTADO=""
for _ in $(seq 1 24); do
  ESTADO=$(docker inspect -f '{{.State.Health.Status}}' "$CONT")
  [ "$ESTADO" = healthy ] && break
  sleep 5
done
[ "$ESTADO" = healthy ] && ok "HEALTHCHECK = healthy" || fallo "HEALTHCHECK = $ESTADO"

# 7. Aunque la plataforma ponga ATALAYA_MODE=gmail, la imagen sigue en modo demo
CONT2=$(docker run -d -e PORT=8001 -e ATALAYA_MODE=gmail -p 8001:8001 "$IMG")
if espera_health 8001; then
  SALUD2=$(curl -fsS "http://127.0.0.1:8001/health" | jq -cS .)
  [ "$SALUD2" = '{"auth":false,"mode":"demo","status":"ok"}' ] \
    && ok "con ATALAYA_MODE=gmail sigue en demo" \
    || fallo "con ATALAYA_MODE=gmail respondio: $SALUD2"
else
  fallo "con ATALAYA_MODE=gmail la imagen no arranco"
  docker logs "$CONT2" || true
fi

echo
[ "$FALLOS" = 0 ] && echo "Imagen correcta." || { echo "$FALLOS comprobacion(es) fallaron."; exit 1; }
