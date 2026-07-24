#!/usr/bin/env bash
set -Eeuo pipefail

# Cuyum v1.2a Transparente - ordenar, cuarentenar y auditar nombres
# ------------------------------------------------------------------
# Objetivo:
#   - Ordenar la raíz del proyecto para capacitación.
#   - Ignorar venv/ por completo para no llenar la terminal con librerías externas.
#   - Generar un plan de nombres Python: archivos en español, nombres largos o poco trazables.
#   - Conservar runtime/logs en raíz hasta adaptar rutas del código.
#
# Regla de seguridad:
#   Este script NO renombra archivos .py automáticamente.
#   Primero produce docs/PLAN_RENOMBRES_PY_V1_2.md para revisar dependencias.
#
# Uso recomendado:
#   cd ~
#   cp -a cuyum_v_1_1 cuyum_v_1_2
#   cd ~/cuyum_v_1_2
#   bash ~/Downloads/cuyum_v1_2a_ordenar_y_auditar_nombres.sh --dry-run
#   bash ~/Downloads/cuyum_v1_2a_ordenar_y_auditar_nombres.sh --name-audit
#   bash ~/Downloads/cuyum_v1_2a_ordenar_y_auditar_nombres.sh --apply
#
# Opciones:
#   --dry-run       Muestra qué haría, sin modificar nada. Es el modo por defecto.
#   --apply         Crea carpetas, mueve archivos no operativos y limpia cachés propios.
#   --name-audit    Solo genera el plan de renombrado Python, sin mover nada.
#   --all           Hace dry-run/apply según MODE y además genera plan de nombres.
#   --quarantine-venv  Mueve venv/ a laboratorio/entornos_locales/ solamente con --apply.
#
# No ejecutar dentro de cuyum_v_1_1.

PROJECT_DIR="$(pwd)"
PROJECT_NAME="$(basename "$PROJECT_DIR")"
MODE="dry-run"
NAME_AUDIT="no"
QUARANTINE_VENV="no"

for arg in "${@:-}"; do
  case "$arg" in
    --dry-run) MODE="dry-run" ;;
    --apply) MODE="apply" ;;
    --name-audit) NAME_AUDIT="only" ;;
    --all) NAME_AUDIT="yes" ;;
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
NAME_REPORT="docs/PLAN_RENOMBRES_PY_V1_2.md"
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

# Evita que el dry-run liste el mismo archivo dos veces cuando coincide con varios patrones.
declare -A PLAN_MOVES=()

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

# Núcleo operativo actual. Todavía conserva nombres reales de v1.1 para no romper arranque.
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

is_ignored_path() {
  local path="$1"
  case "$path" in
    ./venv/*|./venv|venv/*|venv) return 0 ;;
    ./.git/*|./.git|.git/*|.git) return 0 ;;
    ./laboratorio/*|./laboratorio|laboratorio/*|laboratorio) return 0 ;;
    ./data/runtime/*|./data/runtime|data/runtime/*|data/runtime) return 0 ;;
    *) return 1 ;;
  esac
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
  is_ignored_path "$src" && return 0

  local key="$src"
  if [[ -n "${PLAN_MOVES[$key]:-}" ]]; then
    return 0
  fi
  PLAN_MOVES[$key]=1

  if [[ "$MODE" == "apply" ]]; then
    mkdir -p "$dest_dir"
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
  is_ignored_path "$src" && return 0

  if [[ "$MODE" == "apply" ]]; then
    rm -rf "$src"
    log_line "- eliminado cache regenerable: $src"
  else
    echo "[dry-run] eliminar cache regenerable: $src"
  fi
}

suggest_name() {
  local file="$1"
  case "$file" in
    servidor_json_seedlink.py) echo "server.py" ;;
    zona_grupo_01_seedlink_adaptativo_v2.py) echo "local_cell_reader.py" ;;
    descubridor_seedlink.py) echo "seedlink_discovery.py" ;;
    inventario_seedlink_vivo.py) echo "seedlink_inventory_live.py" ;;
    generar_inventory_auto_cell_01.py) echo "generate_auto_cell_inventory.py" ;;
    buscar_estaciones_mendoza.py) echo "find_mendoza_stations.py" ;;
    calibrar_seedlink_cercanos.py) echo "calibrate_nearby_seedlink.py" ;;
    confirmar_cell02_v4d.py) echo "confirm_cell02.py" ;;
    probar_seedlink_candidatos.py) echo "test_seedlink_candidates.py" ;;
    simulador_evento.py) echo "event_simulator.py" ;;
    servidor_json_completo_demo.py) echo "demo_server.py" ;;
    monitor_central_completo_demo.py) echo "demo_monitor.py" ;;
    zona_grupo_01_fdsn_demo.py) echo "demo_fdsn_local_cell.py" ;;
    zona_grupo_01_seedlink_adaptativo.py) echo "local_cell_reader_legacy.py" ;;
    test_01_fdsn_historico.py) echo "test_fdsn_history.py" ;;
    test_02_energia.py) echo "test_signal_energy.py" ;;
    test_03_json_local.py) echo "test_local_json.py" ;;
    test_04_monitor_central_local.py) echo "test_local_monitor.py" ;;
    test_05_servidor_json_local.py) echo "test_local_server.py" ;;
    test_fdsn_reciente_mendoza.py) echo "test_recent_mendoza_fdsn.py" ;;
    *) echo "" ;;
  esac
}

name_reason() {
  local file="$1"
  local reasons=()
  [[ "$file" =~ (buscar|calibrar|confirmar|inventario|generar|probar|simulador|servidor|completo|monitor|zona|grupo|historico|energia|reciente|cercanos|vivo) ]] && reasons+=("nombre en español")
  [[ "$file" =~ (_v[0-9]|_v[0-9][a-z]|adaptativo|completo|demo|local) ]] && reasons+=("nombre histórico o largo")
  [[ ${#file} -gt 32 ]] && reasons+=("demasiado largo")
  if [[ ${#reasons[@]} -eq 0 ]]; then
    echo "sin observación fuerte"
  else
    local IFS=", "
    echo "${reasons[*]}"
  fi
}

rename_stage() {
  local file="$1"
  case "$file" in
    servidor_json_seedlink.py|zona_grupo_01_seedlink_adaptativo_v2.py)
      echo "posponer: núcleo llamado por scripts de arranque" ;;
    public_live.py|event_journal.py|multicell_fusion.py|retention_cleaner.py|sensor_auditor.py|auto_cell_reader_seedlink.py|cuyum_auto_cells.py)
      echo "conservar: ya está en inglés o aceptable" ;;
    test_*.py|cell_manager_dry_run*.py|seedlink_probe*.py|buscar_*.py|calibrar_*.py|confirmar_*.py|probar_*.py|*_demo.py|zona_grupo_01_fdsn_demo.py)
      echo "mover primero a laboratorio; renombrar después si se conserva" ;;
    *)
      echo "evaluar manualmente" ;;
  esac
}

import_references() {
  local module="$1"
  local base="${module%.py}"
  # Cuenta referencias simples sin entrar a venv/laboratorio.
  find . \
    -path './venv' -prune -o \
    -path './.git' -prune -o \
    -path './laboratorio' -prune -o \
    -type f \( -name '*.py' -o -name '*.sh' -o -name '*.js' -o -name '*.html' \) \
    -print0 2>/dev/null | \
  xargs -0 grep -E "(import ${base}|from ${base} import|${module})" 2>/dev/null | wc -l | tr -d ' '
}

generate_name_audit() {
  mkdir -p docs
  cat > "$NAME_REPORT" <<EOF_REPORT
# Plan de nombres Python para Cuyum v1.2 Transparente

Fecha: $TIMESTAMP  
Carpeta: $PROJECT_DIR
EOF_REPORT

  cat >> "$NAME_REPORT" <<'EOF_REPORT'

## Criterio

Este documento no renombra nada por sí solo. Su objetivo es detectar archivos `.py` con nombres en español, nombres históricos o nombres largos, y proponer una transición hacia nombres más trazables para capacitación.

Regla de seguridad:

- Primero se mueve lo experimental a `laboratorio/`.
- Después se prueban los scripts de arranque.
- Recién al final se renombran archivos del núcleo.
- Si un archivo es importado o llamado por scripts, no se renombra sin actualizar referencias.

## Archivos Python revisados

| Archivo actual | Propuesta posible | Motivo | Referencias detectadas | Criterio |
|---|---|---:|---:|---|
EOF_REPORT

  while IFS= read -r -d '' path; do
    local file suggested reason refs stage
    file="$(basename "$path")"
    suggested="$(suggest_name "$file")"
    [[ -z "$suggested" ]] && suggested="—"
    reason="$(name_reason "$file")"
    refs="$(import_references "$file")"
    stage="$(rename_stage "$file")"
    printf '| `%s` | `%s` | %s | %s | %s |\n' "$file" "$suggested" "$reason" "$refs" "$stage" >> "$NAME_REPORT"
  done < <(find . \
    -path './venv' -prune -o \
    -path './.git' -prune -o \
    -path './laboratorio' -prune -o \
    -type f -name '*.py' -print0 2>/dev/null | sort -z)

  cat >> "$NAME_REPORT" <<'EOF_REPORT'

## Recomendación de nomenclatura v1.2

Para módulos Python de Cuyum, usar inglés técnico simple en `snake_case`:

```text
server.py
public_live.py
event_journal.py
multicell_fusion.py
retention_cleaner.py
sensor_auditor.py
auto_cell_reader.py
local_cell_reader.py
seedlink_discovery.py
seedlink_inventory.py
event_simulator.py
```

No usar en archivos operativos:

```text
zona_grupo_01_...
servidor_json_...
adaptativo_v2
completo_demo
historico
reciente
cercanos
```

Esos nombres pueden quedar en `laboratorio/` si son parte de la historia del proyecto.

## Orden seguro de renombrado

1. No renombrar todavía archivos llamados por scripts de inicio.
2. Mover pruebas y experimentos a `laboratorio/`.
3. Probar arranque completo de v1.2.
4. Renombrar un solo archivo central por vez.
5. Actualizar imports y scripts.
6. Probar endpoints:

```bash
curl http://127.0.0.1:5000/api/public/live | head
curl http://127.0.0.1:5000/api/public/events | head
```

## Idea pedagógica

La raíz de Cuyum debe mostrar archivos con función clara. El nombre del archivo tiene que ayudar a explicar el sistema:

```text
server.py                 publica endpoints
public_live.py            arma el estado vivo
event_journal.py          registra eventos importantes
multicell_fusion.py       combina celdas y sensores
local_cell_reader.py      lee la celda local
retention_cleaner.py      limpia registros antiguos
```
EOF_REPORT

  echo "Plan de nombres generado: $NAME_REPORT"
}

if [[ "$NAME_AUDIT" == "only" ]]; then
  generate_name_audit
  exit 0
fi

if [[ "$MODE" == "apply" ]]; then
  cat > "$REPORT" <<EOF_REPORT
# Reporte de limpieza Cuyum v1.2 Transparente

Fecha: $TIMESTAMP
Carpeta: $PROJECT_DIR
Modo: apply

## Criterio

La limpieza no cambia la lógica operativa de Cuyum. Solo ordena la raíz del proyecto para capacitación, trazabilidad y lectura humana. En v1.2a conserva runtime/logs en raíz para no romper rutas actuales.

## Movimientos realizados

EOF_REPORT
else
  echo "Modo dry-run: no se modifica nada."
  echo "Carpeta: $PROJECT_DIR"
fi

for d in "${mkdir_cmds[@]}"; do
  run_or_print mkdir -p "$d"
done

# Pruebas y scripts de exploración general.
for f in test_*.py prueba_*.py probar_*.py *_test.py; do
  [[ -e "$f" ]] && move_file "$f" "$DIR_PRUEBAS"
done

# Dry-runs / simulaciones / pruebas de manager.
for f in *dry_run*.py *_dryrun*.py dry_run*.py cell_manager_dry_run*.py; do
  [[ -e "$f" ]] && move_file "$f" "$DIR_DRY"
done

# Exploración SeedLink, calibración, búsqueda y confirmaciones puntuales.
for f in seedlink_probe*.py *probe_seedlink*.py buscar_*.py calibrar_*.py confirmar_*.py validar_*.py explorar_*.py inventario_*.py generar_inventory_*.py; do
  [[ -e "$f" ]] && move_file "$f" "$DIR_SEEDLINK"
done

# Demos y simuladores que no son núcleo operativo.
for f in *_demo.py monitor_*_demo.py servidor_*_demo.py simulador_*.py; do
  [[ -e "$f" ]] && move_file "$f" "$DIR_PRUEBAS"
done

# Reportes, notas de hotfix y documentación temporal de parches.
for f in REPORTE* reporte* README_HOTFIX* HOTFIX* PATCH* patch* *_patch.md *_hotfix.md *.diff *.patch; do
  [[ -e "$f" ]] && move_file "$f" "$DIR_HOTFIX"
done

# Backups tar y paquetes generados.
for f in *.tar *.tar.gz *.tgz *.zip; do
  [[ -e "$f" ]] && move_file "$f" "$DIR_TAR"
done

# Runtime y logs: NO se mueven en v1.2a.
# Motivo: el código actual puede seguir buscándolos en la raíz.
# Se migrarán a data/runtime/ recién cuando los módulos lean rutas configurables.
if [[ "$MODE" == "dry-run" ]]; then
  for f in logs_*.txt *.log audit_recent.jsonl events_recent.jsonl daily_summary.jsonl event_journal_state.json state_*.json; do
    [[ -e "$f" ]] && echo "[dry-run] conservar runtime en raíz por seguridad: $f"
  done
else
  log_line ""
  log_line "## Runtime conservado en raíz"
  log_line ""
  log_line "Los logs, JSONL y archivos state_*.json se conservaron en raíz en v1.2a para no romper rutas actuales."
fi

# Temporales sueltos.
for f in *.tmp *.bak *.old *.orig nohup.out; do
  [[ -e "$f" ]] && move_file "$f" "$DIR_DESCARTES"
done

# Cachés Python propios: ignora venv/, .git/, laboratorio/ y data/runtime/.
while IFS= read -r -d '' d; do
  remove_path "$d"
done < <(find . \
  -path './venv' -prune -o \
  -path './.git' -prune -o \
  -path './laboratorio' -prune -o \
  -path './data/runtime' -prune -o \
  -type d -name '__pycache__' -print0 2>/dev/null)

while IFS= read -r -d '' f; do
  remove_path "$f"
done < <(find . \
  -path './venv' -prune -o \
  -path './.git' -prune -o \
  -path './laboratorio' -prune -o \
  -path './data/runtime' -prune -o \
  -type f -name '*.pyc' -print0 2>/dev/null)

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
    echo "venv detectado: se conserva entero y no se inspecciona por dentro."
    echo "Para una exportación limpia, usar tools/exportar_cuyum_limpio.sh o excluir venv/."
    if [[ "$MODE" == "apply" ]]; then
      log_line ""
      log_line "## venv"
      log_line ""
      log_line "Se conservó venv/ entero en raíz para no romper scripts actuales. No debe subirse a Git ni incluirse en paquetes educativos."
    fi
  fi
fi

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
fi

if [[ "$NAME_AUDIT" == "yes" ]]; then
  generate_name_audit
fi

if [[ "$MODE" == "apply" ]]; then
  cat >> "$REPORT" <<EOF_REPORT

## Próximo paso sugerido

1. Probar que Cuyum v1.2 todavía inicia.
2. Revisar que /live, /api/public/live y /api/public/events respondan.
3. Revisar docs/PLAN_RENOMBRES_PY_V1_2.md antes de renombrar archivos centrales.
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
else
  echo ""
  echo "Dry-run terminado. Si el plan es correcto, ejecutá:"
  echo "  bash $0 --apply"
  echo "Para auditar nombres Python sin mover nada:"
  echo "  bash $0 --name-audit"
fi
