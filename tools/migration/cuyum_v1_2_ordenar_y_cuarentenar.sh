#!/usr/bin/env bash
set -Eeuo pipefail

# Cuyum v1.2 Transparente - Ordenar y cuarentenar
# --------------------------------------------------
# Este script limpia la RAÍZ del proyecto sin modificar la lógica operativa.
# Mueve archivos históricos, pruebas, hotfixes y reportes a laboratorio/.
# Borra cachés Python regenerables.
# NO borra código operativo.
# NO toca cuyum_v_1_1.
#
# Uso recomendado:
#   cd ~
#   cp -a cuyum_v_1_1 cuyum_v_1_2
#   cd ~/cuyum_v_1_2
#   bash tools/cuyum_v1_2_ordenar_y_cuarentenar.sh --dry-run
#   bash tools/cuyum_v1_2_ordenar_y_cuarentenar.sh --apply
#
# Si todavía no está dentro de tools/, también puede ejecutarse desde la raíz:
#   bash cuyum_v1_2_ordenar_y_cuarentenar.sh --dry-run
#   bash cuyum_v1_2_ordenar_y_cuarentenar.sh --apply

PROJECT_DIR="$(pwd)"
PROJECT_NAME="$(basename "$PROJECT_DIR")"
MODE="dry-run"
QUARANTINE_VENV="no"

for arg in "${@:-}"; do
  case "$arg" in
    --dry-run) MODE="dry-run" ;;
    --apply) MODE="apply" ;;
    --quarantine-venv) QUARANTINE_VENV="yes" ;;
    -h|--help)
      sed -n '1,45p' "$0"
      exit 0
      ;;
    *)
      echo "Argumento no reconocido: $arg" >&2
      exit 1
      ;;
  esac
done

if [[ "$PROJECT_NAME" == "cuyum_v_1_1" ]]; then
  echo "ERROR: estás parado en cuyum_v_1_1." >&2
  echo "Este script está pensado para una COPIA, por ejemplo ~/cuyum_v_1_2." >&2
  exit 2
fi

if [[ ! -f "servidor_json_seedlink.py" && ! -f "public_live.py" ]]; then
  echo "ERROR: no parece ser la raíz de Cuyum." >&2
  echo "Entrá a la carpeta del proyecto antes de ejecutar." >&2
  exit 2
fi

REPORT="REPORTE_LIMPIEZA_V1_2.md"
TIMESTAMP="$(date -Iseconds)"

LAB="laboratorio"
DIR_PRUEBAS="$LAB/pruebas"
DIR_DRY="$LAB/dry_runs"
DIR_SEEDLINK="$LAB/exploracion_seedlink"
DIR_REPORTES="$LAB/reportes_antiguos"
DIR_HOTFIX="$LAB/hotfixes_y_patches"
DIR_TAR="$LAB/backups_tar"
DIR_RUNTIME="data/runtime"
DIR_CACHE="$LAB/cache_python"
DIR_DESCARTES="$LAB/descartes_temporales"
DIR_ENTORNOS="$LAB/entornos_locales"

mkdir_cmds=(
  "docs"
  "tools"
  "config"
  "data"
  "$DIR_PRUEBAS"
  "$DIR_DRY"
  "$DIR_SEEDLINK"
  "$DIR_REPORTES"
  "$DIR_HOTFIX"
  "$DIR_TAR"
  "$DIR_RUNTIME"
  "$DIR_CACHE"
  "$DIR_DESCARTES"
  "$DIR_ENTORNOS"
)

CORE_FILES=(
  "servidor_json_seedlink.py"
  "public_live.py"
  "event_journal.py"
  "multicell_fusion.py"
  "retention_cleaner.py"
  "sensor_auditor.py"
  "auto_cell_reader_seedlink.py"
  "zona_grupo_01_seedlink_adaptativo_v2.py"
  "descubridor_periodico.sh"
  "detener_cuyum_v1_1.sh"
  "iniciar_cuyum_visible_v1_1.sh"
  "sensor_geo_overrides.json"
  "templates"
  "static"
  "docs"
  "tools"
  "config"
  "data"
  "laboratorio"
  "VERSION.md"
  "README.md"
  "README_V1_2_TRANSPARENTE.md"
  "requirements.txt"
  ".gitignore"
)

is_core() {
  local base="$1"
  for f in "${CORE_FILES[@]}"; do
    [[ "$base" == "$f" ]] && return 0
  done
  return 1
}

log_line() {
  local text="$1"
  echo "$text" | tee -a "$REPORT" >/dev/null
}

run_or_print() {
  if [[ "$MODE" == "apply" ]]; then
    "$@"
  else
    printf '[dry-run]'
    printf ' %q' "$@"
    printf '\n'
  fi
}

move_file() {
  local src="$1"
  local dest_dir="$2"
  local base
  base="$(basename "$src")"

  [[ ! -e "$src" ]] && return 0
  is_core "$base" && return 0

  if [[ "$MODE" == "apply" ]]; then
    mkdir -p "$dest_dir"
    # Evita pisar si ya existía algo con el mismo nombre.
    local dest="$dest_dir/$base"
    if [[ -e "$dest" ]]; then
      dest="$dest_dir/${base}.migrado_$(date +%Y%m%d_%H%M%S)"
    fi
    mv "$src" "$dest"
    log_line "- $src → $dest"
  else
    echo "[dry-run] mover: $src → $dest_dir/$base"
  fi
}

remove_path() {
  local src="$1"
  [[ ! -e "$src" ]] && return 0
  if [[ "$MODE" == "apply" ]]; then
    rm -rf "$src"
    log_line "- eliminado cache regenerable: $src"
  else
    echo "[dry-run] eliminar cache regenerable: $src"
  fi
}

# Reporte nuevo
if [[ "$MODE" == "apply" ]]; then
  cat > "$REPORT" <<EOF_REPORT
# Reporte de limpieza Cuyum v1.2 Transparente

Fecha: $TIMESTAMP
Carpeta: $PROJECT_DIR
Modo: apply

## Criterio

La limpieza no cambia la lógica operativa de Cuyum. Solo ordena la raíz del proyecto para capacitación, trazabilidad y lectura humana.

## Movimientos realizados

EOF_REPORT
else
  echo "Modo dry-run: no se modifica nada."
  echo "Carpeta: $PROJECT_DIR"
fi

# Carpetas base
for d in "${mkdir_cmds[@]}"; do
  run_or_print mkdir -p "$d"
done

# Pruebas y scripts de exploración general
for f in test_*.py prueba_*.py probar_*.py *_test.py; do
  [[ -e "$f" ]] && move_file "$f" "$DIR_PRUEBAS"
done

# Dry-runs / simulaciones / pruebas de manager
for f in *dry_run*.py *_dryrun*.py dry_run*.py cell_manager_dry_run*.py; do
  [[ -e "$f" ]] && move_file "$f" "$DIR_DRY"
done

# Exploración SeedLink, calibración, búsqueda y confirmaciones puntuales
for f in seedlink_probe*.py *probe_seedlink*.py buscar_*.py calibrar_*.py confirmar_*.py validar_*.py explorar_*.py; do
  [[ -e "$f" ]] && move_file "$f" "$DIR_SEEDLINK"
done

# Reportes, notas de hotfix y documentación temporal de parches
for f in REPORTE* reporte* README_HOTFIX* HOTFIX* PATCH* patch* *_patch.md *_hotfix.md *.diff *.patch; do
  [[ -e "$f" ]] && move_file "$f" "$DIR_HOTFIX"
done

# Backups tar y paquetes generados
for f in *.tar *.tar.gz *.tgz *.zip; do
  [[ -e "$f" ]] && move_file "$f" "$DIR_TAR"
done

# Logs y archivos runtime con crecimiento potencial
# Se mueven a data/runtime para que no contaminen la raíz.
for f in logs_*.txt *.log audit_recent.jsonl events_recent.jsonl daily_summary.jsonl event_journal_state.json state_*.json; do
  [[ -e "$f" ]] && move_file "$f" "$DIR_RUNTIME"
done

# Archivos temporales sueltos
for f in *.tmp *.bak *.old *.orig nohup.out; do
  [[ -e "$f" ]] && move_file "$f" "$DIR_DESCARTES"
done

# Cachés Python regenerables: se eliminan, no se guardan.
while IFS= read -r -d '' d; do
  remove_path "$d"
done < <(find . -type d -name '__pycache__' -print0 2>/dev/null)

while IFS= read -r -d '' f; do
  remove_path "$f"
done < <(find . -type f -name '*.pyc' -print0 2>/dev/null)

# venv: por defecto NO se toca para no romper scripts actuales.
# Puede moverse con --quarantine-venv, pero solo en una copia v1.2.
if [[ -d "venv" ]]; then
  if [[ "$QUARANTINE_VENV" == "yes" ]]; then
    move_file "venv" "$DIR_ENTORNOS"
    if [[ "$MODE" == "apply" ]]; then
      log_line ""
      log_line "Advertencia: venv fue movido a laboratorio/entornos_locales/. Si los scripts usan ./venv, habrá que recrearlo o ajustar rutas."
    else
      echo "[dry-run] venv sería movido por --quarantine-venv."
    fi
  else
    echo "venv detectado: se conserva en raíz para no romper arranque."
    echo "Para una exportación limpia, usar tools/exportar_cuyum_limpio.sh o excluir venv/."
    if [[ "$MODE" == "apply" ]]; then
      log_line ""
      log_line "## venv"
      log_line ""
      log_line "Se conservó venv/ en raíz para no romper scripts actuales. No debe subirse a Git ni incluirse en paquetes educativos."
    fi
  fi
fi

# Crear .gitignore si no existe, o reforzarlo sin duplicar líneas.
if [[ "$MODE" == "apply" ]]; then
  touch .gitignore
  for line in \
    "venv/" \
    "__pycache__/" \
    "*.pyc" \
    "*.tar" \
    "*.tar.gz" \
    "*.tgz" \
    "*.zip" \
    "logs_*.txt" \
    "*.log" \
    "data/runtime/" \
    "audit_recent.jsonl" \
    "events_recent.jsonl" \
    "daily_summary.jsonl" \
    "event_journal_state.json" \
    "config/*.local.json" \
    "esp32/config.h"; do
    grep -qxF "$line" .gitignore || echo "$line" >> .gitignore
  done
  log_line ""
  log_line "## Archivos conservados en raíz"
  log_line ""
  for f in "${CORE_FILES[@]}"; do
    [[ -e "$f" ]] && log_line "- $f"
  done
else
  echo ""
  echo "Dry-run terminado. Si el plan es correcto, ejecutá:"
  echo "  bash $0 --apply"
fi

if [[ "$MODE" == "apply" ]]; then
  cat >> "$REPORT" <<EOF_REPORT

## Próximo paso sugerido

1. Probar que Cuyum v1.2 todavía inicia.
2. Revisar que /live, /api/public/live y /api/public/events respondan.
3. Si algo falla, revisar si algún archivo movido a laboratorio/ era llamado por un script de inicio.
4. No borrar laboratorio/ hasta tener varios arranques correctos.

Comandos sugeridos:

\`\`\`bash
cd "$PROJECT_DIR"
./iniciar_cuyum_visible_v1_1.sh
curl http://127.0.0.1:5000/api/public/live | head
curl http://127.0.0.1:5000/api/public/events | head
\`\`\`
EOF_REPORT
  echo "Listo. Reporte generado: $REPORT"
fi
