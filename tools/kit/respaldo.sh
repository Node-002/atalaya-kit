#!/usr/bin/env bash
# Respaldo consistente de la base de datos de Atalaya (SQLite) con la API de copia de SQLite.
# Uso (desde la carpeta del kit):  tools/kit/respaldo.sh [carpeta_de_destino]
#
# - Copia SOLO la base (veredictos, estado, tokens de Google CIFRADOS). No copia la clave Fernet.
# - GUARDA LA CLAVE ATALAYA_FERNET_KEY APARTE (gestor de contrasenas). Sin ella, los tokens del
#   respaldo son ilegibles: habria que reconectar todos los buzones. Y no guardes la clave junto al
#   respaldo: quien tenga ambos puede leer los tokens.
# - Funciona con el contenedor en marcha (no hace falta detenerlo). No necesita el programa sqlite3.
set -euo pipefail

DESTINO="${1:-respaldos}"
SERVICIO="${ATALAYA_SERVICIO:-atalaya}"
mkdir -p "$DESTINO"
chmod 700 "$DESTINO"
ARCHIVO="$DESTINO/atalaya-$(date +%Y%m%d-%H%M%S).db"
umask 077

# La copia se hace DENTRO del contenedor (en /tmp, que esta en memoria) y se verifica antes de salir.
docker compose exec -T "$SERVICIO" python -c '
import os, sqlite3, sys, tempfile
ruta = os.environ.get("ATALAYA_DB_PATH", "/srv/data/atalaya.db")
fd, tmp = tempfile.mkstemp(dir="/tmp"); os.close(fd)
origen = sqlite3.connect("file:%s?mode=ro" % ruta, uri=True)
copia = sqlite3.connect(tmp)
origen.backup(copia)
estado = copia.execute("PRAGMA integrity_check").fetchone()[0]
copia.close(); origen.close()
if estado != "ok":
    sys.stderr.write("La copia no paso la verificacion de integridad: %s\n" % estado); sys.exit(2)
sys.stdout.buffer.write(open(tmp, "rb").read()); os.remove(tmp)
' > "$ARCHIVO"

if [ ! -s "$ARCHIVO" ]; then
  rm -f "$ARCHIVO"
  echo "ERROR: el respaldo salio vacio. Esta en marcha el contenedor? (docker compose ps)" >&2
  exit 1
fi
echo "Respaldo creado: $ARCHIVO ($(wc -c < "$ARCHIVO") bytes)"
echo "Recuerda: la clave ATALAYA_FERNET_KEY NO esta incluida; guardala aparte."
