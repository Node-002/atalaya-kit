#!/usr/bin/env bash
# Restaura un respaldo hecho con respaldo.sh. REEMPLAZA la base actual.
# Uso (desde la carpeta del kit):  tools/kit/restaurar.sh respaldos/atalaya-AAAAMMDD-HHMMSS.db
#
# Requiere la MISMA clave ATALAYA_FERNET_KEY con la que se hizo el respaldo; con otra, los tokens
# de Google guardados no se pueden descifrar y hay que reconectar los buzones.
set -euo pipefail

ARCHIVO="${1:?Uso: restaurar.sh <archivo_de_respaldo.db>}"
SERVICIO="${ATALAYA_SERVICIO:-atalaya}"
[ -s "$ARCHIVO" ] || { echo "ERROR: no existe o esta vacio: $ARCHIVO" >&2; exit 1; }
# Un archivo SQLite empieza con esta cabecera.
[ "$(head -c 15 "$ARCHIVO")" = "SQLite format 3" ] || { echo "ERROR: $ARCHIVO no parece una base SQLite." >&2; exit 1; }

read -r -p "Esto REEMPLAZA la base de datos actual de Atalaya. Escribe SI para continuar: " RESP
[ "$RESP" = "SI" ] || { echo "Cancelado."; exit 1; }

docker compose stop "$SERVICIO"
# Contenedor temporal (mismo volumen, sin la comprobacion de arranque) que escribe la base y borra restos -wal/-shm.
docker compose run --rm --no-deps -T --entrypoint "" "$SERVICIO" sh -c '
  set -e
  destino="${ATALAYA_DB_PATH:-/srv/data/atalaya.db}"
  cat > "$destino.nuevo"
  rm -f "$destino-wal" "$destino-shm"
  mv "$destino.nuevo" "$destino"
' < "$ARCHIVO"
docker compose up -d "$SERVICIO"
echo "Restaurado. Comprueba:  python3 tools/kit/verificar_instalacion.py --env-file .env.kit"
