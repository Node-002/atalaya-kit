#!/usr/bin/env bash
# Lanza el asistente de instalacion del kit de Atalaya (tools/kit/instalar.py).
# Launches the Atalaya kit installation assistant. Uso / Usage:  tools/kit/instalar.sh [opciones / options]
# Solo busca Python 3.9+; si falta, explica como obtenerlo y NO descarga ni instala nada.
set -euo pipefail

AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

for candidato in python3 python; do
  if command -v "$candidato" >/dev/null 2>&1 \
     && "$candidato" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' >/dev/null 2>&1; then
    exec "$candidato" "$AQUI/instalar.py" "$@"
  fi
done

if [[ "${ATALAYA_LANG:-es}" == en* ]] || { [ "${1:-}" = "--lang" ] && [ "${2:-}" = "en" ]; }; then
  cat >&2 <<'MSG'
Python 3.9 or newer was not found. This assistant installs nothing by itself.
Get Python from your system's package manager and run this script again:
  Debian/Ubuntu:  sudo apt install python3
  Fedora/RHEL:    sudo dnf install python3
  macOS:          brew install python   (or https://www.python.org/downloads/)
MSG
else
  cat >&2 <<'MSG'
No se encontro Python 3.9 o superior. Este asistente no instala nada por su cuenta.
Obtenlo con el gestor de paquetes de tu sistema y vuelve a ejecutar este script:
  Debian/Ubuntu:  sudo apt install python3
  Fedora/RHEL:    sudo dnf install python3
  macOS:          brew install python   (o https://www.python.org/downloads/)
MSG
fi
exit 1
