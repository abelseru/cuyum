#!/usr/bin/env bash
set -euo pipefail

MODE="${1:---dry-run}"
if [[ "$MODE" != "--dry-run" && "$MODE" != "--apply" ]]; then
  echo "Uso: bash cuyum_v1_2_aislar_rutas_operativas.sh --dry-run|--apply" >&2
  exit 2
fi

ROOT="$(pwd)"
PROJECT_NAME="$(basename "$ROOT")"
REPORT="REPORTE_AISLAMIENTO_V1_2.md"
STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="laboratorio/hotfixes_y_patches/backup_aislamiento_v1_2_$STAMP"

need_file() {
  [[ -f "$1" ]] || { echo "ERROR: falta $1. Ejecutá esto desde la raíz de Cuyum." >&2; exit 1; }
}

need_file "servidor_json_seedlink.py"
need_file "public_live.py"
need_file "event_journal.py"

if [[ "$PROJECT_NAME" == "cuyum_v_1_1" ]]; then
  echo "ERROR: estás parado en cuyum_v_1_1. Este script es solo para la copia v1.2." >&2
  exit 1
fi

if [[ "$PROJECT_NAME" != *"1_2"* && "$PROJECT_NAME" != *"v_1_2"* ]]; then
  echo "ADVERTENCIA: la carpeta no parece llamarse cuyum_v_1_2: $PROJECT_NAME" >&2
  echo "Continuo porque los archivos núcleo existen." >&2
fi

log() { echo "$*"; }

patch_one() {
  local src="$1"
  local dst="$2"
  local inplace="$3"

  if [[ ! -f "$src" ]]; then
    log "[omitir] no existe $src"
    return 0
  fi

  if [[ "$MODE" == "--dry-run" ]]; then
    if [[ "$src" == "$dst" ]]; then
      log "[dry-run] parchear en sitio: $src"
    else
      log "[dry-run] crear $dst desde $src y corregir rutas v1.2"
    fi
    return 0
  fi

  mkdir -p "$BACKUP_DIR"
  cp -a "$src" "$BACKUP_DIR/$(basename "$src")"
  cp -a "$src" "$dst"

  python3 - "$dst" <<'PY'
from pathlib import Path
import re, sys

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8", errors="replace")
lines = text.splitlines(keepends=True)

# Insertar BASE_DIR después del shebang si el script no lo tiene.
out = []
inserted = False
i = 0
if lines and lines[0].startswith("#!"):
    out.append(lines[0])
    i = 1
    if "BASE_DIR=" not in text:
        out.append('# Cuyum v1.2: usar siempre la carpeta donde vive este script.\n')
        out.append('BASE_DIR="$(cd "$(dirname "$0")" && pwd)"\n')
        inserted = True
elif "BASE_DIR=" not in text:
    out.append('# Cuyum v1.2: usar siempre la carpeta donde vive este script.\n')
    out.append('BASE_DIR="$(cd "$(dirname "$0")" && pwd)"\n')
    inserted = True

# Reemplazar bloques cd /home/usuario/cuyum_v_1_1 || { ... }
while i < len(lines):
    line = lines[i]
    stripped = line.strip()
    if re.match(r'^cd\s+(~/cuyum_v_1_1|/home/usuario/cuyum_v_1_1)\s*\|\|\s*\{\s*$', stripped):
        out.append('cd "$BASE_DIR" || exit 1\n')
        i += 1
        # saltar hasta el cierre del bloque
        while i < len(lines):
            if lines[i].strip() == "}":
                i += 1
                break
            i += 1
        continue
    if re.match(r'^cd\s+(~/cuyum_v_1_1|/home/usuario/cuyum_v_1_1)\s*\|\|\s*exit\s+1\s*$', stripped):
        out.append('cd "$BASE_DIR" || exit 1\n')
        i += 1
        continue
    if re.match(r'^cd\s+(~/cuyum_v_1_1|/home/usuario/cuyum_v_1_1)\s*$', stripped):
        out.append('cd "$BASE_DIR" || exit 1\n')
        i += 1
        continue
    out.append(line)
    i += 1

text = ''.join(out)
# Ajustes de nombre visibles y llamadas entre scripts operativos.
repls = {
    'detener_cuyum_v1_1.sh': 'detener_cuyum_v1_2.sh',
    'iniciar_cuyum_visible_v1_1.sh': 'iniciar_cuyum_visible_v1_2.sh',
    'ver_multicelda_v1_1.sh': 'ver_multicelda_v1_2.sh',
    'cuyum_v_1_1': 'cuyum_v_1_2',
    'CUYUM v1.1c': 'CUYUM v1.2',
    'CUYUM v1.1': 'CUYUM v1.2',
    'Cuyum v1.1': 'Cuyum v1.2',
    'v1.1': 'v1.2',
}
for a,b in repls.items():
    text = text.replace(a,b)

path.write_text(text, encoding="utf-8")
PY

  chmod +x "$dst"
  bash -n "$dst"
  if [[ "$src" == "$dst" ]]; then
    log "[ok] parcheado en sitio: $dst"
  else
    log "[ok] creado: $dst"
  fi
}

if [[ "$MODE" == "--apply" ]]; then
  mkdir -p laboratorio/hotfixes_y_patches
fi

patch_one "iniciar_cuyum_visible_v1_1.sh" "iniciar_cuyum_visible_v1_2.sh" "copy"
patch_one "detener_cuyum_v1_1.sh" "detener_cuyum_v1_2.sh" "copy"
patch_one "ver_multicelda_v1_1.sh" "ver_multicelda_v1_2.sh" "copy"
patch_one "arrancar_sistema.sh" "arrancar_sistema_v1_2.sh" "copy"
# Este se llama desde el arranque; debe quedar corregido en sitio.
patch_one "descubridor_periodico.sh" "descubridor_periodico.sh" "inplace"

if [[ "$MODE" == "--apply" ]]; then
  cat > "$REPORT" <<EOF
# Reporte de aislamiento operativo Cuyum v1.2

Fecha: $STAMP
Carpeta: $ROOT

## Objetivo

Separar la copia v1.2 de rutas hardcodeadas hacia cuyum_v_1_1 sin renombrar todavía archivos Python núcleo.

## Archivos creados

- iniciar_cuyum_visible_v1_2.sh
- detener_cuyum_v1_2.sh
- ver_multicelda_v1_2.sh
- arrancar_sistema_v1_2.sh, si existía arrancar_sistema.sh

## Archivo parcheado en sitio

- descubridor_periodico.sh

## Copias de seguridad

$BACKUP_DIR

## Verificación sugerida

\`\`\`bash
cd ~/cuyum_v_1_2
grep -R "cuyum_v_1_1" -n iniciar_cuyum_visible_v1_2.sh detener_cuyum_v1_2.sh ver_multicelda_v1_2.sh arrancar_sistema_v1_2.sh descubridor_periodico.sh 2>/dev/null
./detener_cuyum_v1_2.sh
./iniciar_cuyum_visible_v1_2.sh
\`\`\`

## Nota sobre venv

El archivo venv/pyvenv.cfg puede conservar el texto del comando con el que fue creado originalmente. Eso no significa necesariamente que Python ejecute desde v1.1. La prueba importante es que el arranque muestre:

\`\`\`text
Python usado:
/home/usuario/cuyum_v_1_2/venv/bin/python
\`\`\`

EOF
  log "Reporte escrito: $REPORT"
  log "Copias de seguridad: $BACKUP_DIR"
else
  log "Dry-run terminado. Si el plan es correcto, ejecutá:"
  log "  bash $(realpath "$0") --apply"
fi
