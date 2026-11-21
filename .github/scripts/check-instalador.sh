#!/usr/bin/env bash
# Prueba el asistente de instalacion (tools/kit/instalar.py) con datos FALSOS generados aqui.
# Nada de esto se comitea: el JSON de Google falso, las claves y .env.kit se crean en tiempo de ejecucion.
# Uso: .github/scripts/check-instalador.sh   (desde la raiz del repositorio; necesita Docker)
set -euo pipefail

FALLOS=0
TMP="$(mktemp -d)"
ok()    { echo "OK    $1"; }
fallo() { echo "FALLA $1"; FALLOS=$((FALLOS + 1)); }
limpiar() {
  docker compose --profile tls down -v >/dev/null 2>&1 || true
  rm -rf secrets .env.kit .env.kit.bak-* "$TMP"
  git checkout -- Caddyfile 2>/dev/null || true
}
trap limpiar EXIT

fake_json() {  # $1 = destino, $2 = URI de redireccion
  python3 - "$1" "$2" <<'PY'
import json, secrets, sys
json.dump({"web": {"client_id": "falso.apps.googleusercontent.com", "client_secret": secrets.token_hex(12),
                   "redirect_uris": [sys.argv[2]]}}, open(sys.argv[1], "w"))
PY
}

# 1. Modo local, sin preguntas, con Docker real: genera la configuracion, construye, arranca, espera /health, verifica.
fake_json "$TMP/google.json" "http://localhost:8000/auth/google/callback"
python3 tools/kit/instalar.py --si --org "Organizacion CI" --modo local --admin admin.ci@example.org \
  --google-json "$TMP/google.json" --copia-clave "$TMP/clave.txt" --timeout 240 > "$TMP/salida.txt" 2>&1 \
  && ok "el asistente instala y verifica el kit (modo local)" \
  || { cat "$TMP/salida.txt"; fallo "el asistente fallo en modo local"; }
cat "$TMP/salida.txt"

# 2. Ningun secreto en la salida; permisos 600; la copia de la clave existe.
for clave in ATALAYA_FERNET_KEY ATALAYA_SESSION_SECRET; do
  valor="$(grep "^$clave=" .env.kit | cut -d= -f2-)"
  [ -n "$valor" ] && ! grep -qF -- "$valor" "$TMP/salida.txt" \
    && ok "$clave no aparece en la salida del asistente" || fallo "$clave aparece en la salida (o falta)"
done
[ "$(stat -c %a .env.kit)" = 600 ] && ok ".env.kit tiene permisos 600" || fallo ".env.kit no tiene permisos 600"
[ -s "$TMP/clave.txt" ] && ok "se guardo la copia de la clave Fernet" || fallo "falta la copia de la clave"

# 3. No sobrescribe sin confirmacion; --verificar funciona sobre la instalacion hecha.
if python3 tools/kit/instalar.py --si --org X --modo local --admin admin.ci@example.org \
     --google-json "$TMP/google.json" --sin-arranque >/dev/null 2>&1; then
  fallo "el asistente sobrescribio .env.kit sin --sobrescribir"
else ok "no sobrescribe una configuracion existente sin confirmacion"; fi
python3 tools/kit/instalar.py --verificar >/dev/null 2>&1 && ok "--verificar pasa sobre la instalacion" || fallo "--verificar fallo"
docker compose down -v >/dev/null 2>&1

# 4. Modo produccion con Caddy, solo configuracion: el compose con el perfil tls es valido y el Caddyfile cambia.
rm -rf secrets .env.kit
fake_json "$TMP/prod.json" "https://atalaya.example.org/auth/google/callback"
python3 tools/kit/instalar.py --si --sin-arranque --org "Organizacion CI" --modo produccion --dominio atalaya.example.org \
  --proxy caddy --admin admin.ci@example.org --google-json "$TMP/prod.json" >/dev/null 2>&1 \
  && ok "el asistente genera la configuracion de produccion" || fallo "fallo la configuracion de produccion"
grep -q '^ATALAYA_TRUST_PROXY=1$' .env.kit && ok "TRUST_PROXY=1 con Caddy" || fallo "TRUST_PROXY no es 1 con Caddy"
grep -q '^atalaya.example.org {' Caddyfile && ok "el Caddyfile tiene el dominio" || fallo "el Caddyfile no se actualizo"
docker compose --profile tls config -q && ok "docker compose (perfil tls) valido con la configuracion generada" \
  || fallo "compose invalido con la configuracion generada"

[ "$FALLOS" = 0 ] || { echo "$FALLOS comprobacion(es) fallaron."; exit 1; }
echo "Asistente de instalacion verificado."
