#!/usr/bin/env bash
# Comprueba el kit autoalojado (etapa `kit` + docker-compose.yml) con datos FALSOS generados aqui.
# Sin secretos reales: el JSON de Google, las claves y .env.kit se crean en tiempo de ejecucion
# y no se comitean. Uso: .github/scripts/check-kit.sh   (desde la raiz del repositorio)
set -euo pipefail

BASE="http://127.0.0.1:8000"
FALLOS=0
DEMO=""
ok()    { echo "OK    $1"; }
fallo() { echo "FALLA $1"; FALLOS=$((FALLOS + 1)); }
limpiar() {
  docker compose --profile tls down -v >/dev/null 2>&1 || true
  [ -n "$DEMO" ] && docker rm -f "$DEMO" >/dev/null 2>&1 || true
  rm -rf secrets .env.kit
}
trap limpiar EXIT

# 1. Construir la etapa kit y comprobar que NO arranca sin las variables obligatorias.
docker build --target kit -t atalaya-kit:local .
SALIDA=$(docker run --rm atalaya-kit:local 2>&1 || true)
CODIGO=0; docker run --rm atalaya-kit:local >/dev/null 2>&1 || CODIGO=$?
if [ "$CODIGO" != 0 ] && echo "$SALIDA" | grep -q "NO arranca" && echo "$SALIDA" | grep -q "ATALAYA_FERNET_KEY"; then
  ok "sin variables, el kit se niega a arrancar (codigo $CODIGO) con mensaje claro"
else
  fallo "el kit arranco sin variables o no dio el mensaje esperado: $SALIDA"
fi

# 2. Datos FALSOS en tiempo de ejecucion (nada de esto va al repositorio).
mkdir -p secrets
python3 - <<'PY'
import base64, json, os, secrets
json.dump({"web": {"client_id": "falso.apps.googleusercontent.com", "client_secret": secrets.token_hex(12),
                   "redirect_uris": ["http://localhost:8000/auth/google/callback"]}},
          open("secrets/google_client.json", "w"))
with open(".env.kit", "w") as f:
    f.write("ATALAYA_BASE_URL=http://localhost:8000\n")
    f.write("GOOGLE_CLIENT_SECRETS_FILE=/run/secrets/google_client.json\n")
    f.write("ATALAYA_FERNET_KEY=" + base64.urlsafe_b64encode(os.urandom(32)).decode() + "\n")
    f.write("ATALAYA_SESSION_SECRET=" + secrets.token_urlsafe(48) + "\n")
    f.write("ATALAYA_ADMIN_EMAILS=admin.ci@example.org\n")
PY
chmod 644 secrets/google_client.json  # el usuario 10001 del contenedor debe poder leerlo

# 3. Levantar con docker compose (etapa kit) y esperar /health.
docker compose up -d --build
LISTO=0
for _ in $(seq 1 60); do
  curl -fsS "$BASE/health" >/dev/null 2>&1 && { LISTO=1; break; }
  sleep 1
done
if [ "$LISTO" != 1 ]; then
  echo "El kit no respondio en /health en 60 s. Registro:"; docker compose logs atalaya || true; exit 1
fi

SALUD=$(curl -fsS "$BASE/health" | jq -cS .)
[ "$SALUD" = '{"auth":true,"mode":"gmail","status":"ok"}' ] \
  && ok "/health = $SALUD" || fallo "/health inesperado: $SALUD"

# 4. La raiz redirige al inicio de sesion; /docs no existe; sin cabecera Server.
LOC=$(curl -s -o /dev/null -w '%{http_code} %{redirect_url}' "$BASE/")
case "$LOC" in
  30[27]\ */login*) ok "/ redirige a /login ($LOC)" ;;
  *) fallo "/ no redirige a /login: $LOC" ;;
esac
C=$(curl -s -o /dev/null -w '%{http_code}' "$BASE/docs")
[ "$C" = 404 ] && ok "/docs da 404" || fallo "/docs dio $C"
if curl -sI "$BASE/health" | grep -qi '^server:'; then fallo "aparece la cabecera Server"; else ok "no hay cabecera Server"; fi

# 5. Usuario sin privilegios y sistema de archivos de solo lectura salvo el volumen de datos.
UID_PROC=$(docker compose exec -T atalaya id -u)
[ "$UID_PROC" != 0 ] && ok "el proceso corre como uid $UID_PROC (no root)" || fallo "el kit corre como root"
if docker compose exec -T atalaya sh -c 'touch /srv/prueba' >/dev/null 2>&1; then
  fallo "se pudo escribir en /srv (el sistema de archivos no es de solo lectura)"
else ok "no se puede escribir fuera del volumen de datos"; fi
if docker compose exec -T atalaya sh -c 'test -s /srv/data/atalaya.db'; then
  ok "la base de datos esta en el volumen /srv/data"
else fallo "no hay base de datos en /srv/data"; fi

# 6. HEALTHCHECK de la imagen
ID=$(docker compose ps -q atalaya)
ESTADO=""
for _ in $(seq 1 24); do
  ESTADO=$(docker inspect -f '{{.State.Health.Status}}' "$ID")
  [ "$ESTADO" = healthy ] && break
  sleep 5
done
[ "$ESTADO" = healthy ] && ok "HEALTHCHECK = healthy" || fallo "HEALTHCHECK = $ESTADO"

# 7. El respaldo se puede crear con el kit en marcha.
./tools/kit/respaldo.sh "$(mktemp -d)" >/dev/null && ok "respaldo.sh crea un respaldo" || fallo "respaldo.sh fallo"

# 8. La configuracion de Caddy y el perfil tls son validos.
docker compose --profile tls config -q && ok "docker compose (perfil tls) valido" || fallo "compose con perfil tls invalido"
docker run --rm -v "$PWD/Caddyfile:/etc/caddy/Caddyfile:ro" caddy:2 caddy validate --config /etc/caddy/Caddyfile >/dev/null 2>&1 \
  && ok "Caddyfile valido" || fallo "Caddyfile invalido"

docker compose down -v >/dev/null 2>&1

# 9. La etapa por defecto (demo, la que construye Render) sigue en modo demo aunque se pida gmail.
docker build -t atalaya-demo:ci .
DEMO=$(docker run -d -e ATALAYA_MODE=gmail -e PORT=8001 -p 127.0.0.1:8001:8001 atalaya-demo:ci)
for _ in $(seq 1 40); do curl -fsS http://127.0.0.1:8001/health >/dev/null 2>&1 && break; sleep 1; done
SALUD=$(curl -fsS http://127.0.0.1:8001/health | jq -cS .)
[ "$SALUD" = '{"auth":false,"mode":"demo","status":"ok"}' ] \
  && ok "la imagen por defecto sigue en modo demo aunque ATALAYA_MODE=gmail ($SALUD)" \
  || fallo "la imagen por defecto no esta en modo demo: $SALUD"

[ "$FALLOS" = 0 ] || { echo "$FALLOS comprobacion(es) fallaron."; exit 1; }
echo "Kit verificado."
