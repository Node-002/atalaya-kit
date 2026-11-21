#!/usr/bin/env bash
# Limpieza dirigida del historial con git filter-repo, conservando fechas, autores y orden.
# NO hace push. Ver docs/LIMPIEZA_HISTORIAL.md. No contiene datos sensibles: la lista de
# reemplazos se pasa como argumento y debe estar FUERA del repositorio.
#
# Uso (Git Bash):
#   bash tools/historial/limpiar_historial.sh REEMPLAZOS.txt [ORIGEN] [DIRECTORIO_DE_TRABAJO] [RAMA_PARA_PRUEBAS]
#     REEMPLAZOS.txt   archivo con reglas "regex:PATRON==>SUSTITUTO" (fuera del repositorio)
#     ORIGEN           repositorio a limpiar (ruta o URL). Por defecto: el repositorio actual
#     DIRECTORIO       carpeta vacia o inexistente para los espejos. Por defecto: carpeta temporal nueva
#     RAMA             rama del resultado donde correr pytest y ruff. Por defecto: hackathon/mvp
# Requisitos: git, python 3.12, git-filter-repo (pip install git-filter-repo==2.47.0), gitleaks.
# Variables opcionales: SALTAR_PRUEBAS=1 omite el paso (e).
set -euo pipefail

REGLAS="${1:?Falta la ruta del archivo de reemplazos (fuera del repositorio)}"
ORIGEN="${2:-$(git rev-parse --show-toplevel)}"
TRABAJO="${3:-$(mktemp -d)}"
RAMA="${4:-hackathon/mvp}"
AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="${PYTHON:-python}"
INICIO=$(date +%s)

paso() { echo; echo "=== $* ==="; }
[ -f "$REGLAS" ] || { echo "No existe $REGLAS"; exit 2; }
REPO_ACTUAL="$(git rev-parse --show-toplevel 2>/dev/null || true)"
case "$(cd "$(dirname "$REGLAS")" && pwd)/" in
  "$REPO_ACTUAL"/*) echo "El archivo de reemplazos esta dentro del repositorio: muevalo fuera."; exit 2;;
esac
command -v git-filter-repo >/dev/null || { echo "git-filter-repo no esta en el PATH"; exit 2; }
command -v gitleaks >/dev/null || { echo "gitleaks no esta en el PATH"; exit 2; }
mkdir -p "$TRABAJO"
[ -z "$(ls -A "$TRABAJO")" ] || { echo "El directorio de trabajo no esta vacio: $TRABAJO"; exit 2; }
echo "Trabajo en: $TRABAJO"

paso "1. Respaldo del original (espejo con todas las ramas) y copia de las fechas"
git clone --mirror --quiet "$ORIGEN" "$TRABAJO/original.git"
git -C "$TRABAJO/original.git" log --all --topo-order --format='%H %aI %cI %an %s' > "$TRABAJO/original-fechas.txt"
echo "Commits en el original: $(git -C "$TRABAJO/original.git" rev-list --all | wc -l)"
tar -czf "$TRABAJO/original.git.tar.gz" -C "$TRABAJO" original.git
echo "Respaldo comprimido: $TRABAJO/original.git.tar.gz ($(du -h "$TRABAJO/original.git.tar.gz" | cut -f1))"

paso "2. Reescritura en un espejo nuevo (fechas, autores y commits vacios se conservan)"
git clone --mirror --quiet "$TRABAJO/original.git" "$TRABAJO/reescrito.git"
(
  cd "$TRABAJO/reescrito.git"
  git filter-repo --force --prune-empty never --prune-degenerate never \
    --replace-text "$REGLAS" --replace-message "$REGLAS"
)
git -C "$TRABAJO/reescrito.git" log --all --topo-order --format='%H %aI %cI %an %s' > "$TRABAJO/reescrito-fechas.txt"
echo "Mapa de commits: $TRABAJO/reescrito.git/filter-repo/commit-map"

paso "3. Verificaciones (a) coincidencias, (b) fechas/autores/orden, (c) diferencias por commit"
"$PY" -I "$AQUI/verificar_historial.py" --old "$TRABAJO/original.git" --new "$TRABAJO/reescrito.git" --rules "$REGLAS"

paso "4. (d) gitleaks sobre todas las ramas del resultado"
( cd "$TRABAJO/reescrito.git" && gitleaks detect --source . --log-opts="--all" --redact --no-banner )

if [ "${SALTAR_PRUEBAS:-0}" = "1" ]; then
  echo "(e) omitido por SALTAR_PRUEBAS=1"
else
  paso "5. (e) Clon del resultado, entorno nuevo, pytest y ruff en la rama $RAMA"
  git clone --quiet --branch "$RAMA" "$TRABAJO/reescrito.git" "$TRABAJO/prueba"
  "$PY" -m venv "$TRABAJO/venv"
  VPY="$TRABAJO/venv/Scripts/python"; [ -x "$VPY" ] || [ -x "$VPY.exe" ] || VPY="$TRABAJO/venv/bin/python"
  "$VPY" -m pip install --quiet -r "$TRABAJO/prueba/requirements-dev.txt"
  ( cd "$TRABAJO/prueba" && "$VPY" -m pytest -q && "$VPY" -m ruff check . )
fi

FIN=$(date +%s)
paso "LISTO: todas las verificaciones pasaron en $((FIN - INICIO)) s. NO se hizo push."
echo "Siguiente: revisar docs/LIMPIEZA_HISTORIAL.md y, si todo esta bien, ejecutar el push forzado a mano."

# --- Push forzado (NO se ejecuta; copiar y ejecutar a mano despues de revisar) -------------------
# cd "$TRABAJO/reescrito.git"
# git remote add origin https://github.com/Node-002/atalaya.git
# git push --force origin refs/heads/hackathon/mvp:refs/heads/hackathon/mvp
# # Otras ramas que correspondan, una a una:  git push --force origin refs/heads/<rama>:refs/heads/<rama>
# # Etiquetas (si existen):                    git push --force origin --tags
# # NO usar --mirror: intentaria tocar refs/pull/* y refs/remotes/*.
