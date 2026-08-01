#!/usr/bin/env bash
set -Eeuo pipefail

cd /app

mkdir -p runtime runtime/logs persistent

children=()

start_process() {
  "$@" &
  children+=("$!")
}

stop_all() {
  trap - EXIT INT TERM

  echo
  echo "Stopping Cuyum container processes..."

  if ((${#children[@]} > 0)); then
    kill "${children[@]}" 2>/dev/null || true
    wait "${children[@]}" 2>/dev/null || true
  fi
}

trap stop_all EXIT INT TERM

echo "=============================================="
echo "        CUYUM $(cat VERSION 2>/dev/null || echo unknown)"
echo "        Docker"
echo "=============================================="

echo "[1/7] Preparing runtime..."
: > runtime/logs/logs_cuyum_server.txt
: > runtime/logs/logs_lector.txt
: > runtime/logs/logs_descubridor.txt
: > runtime/logs/logs_sensor_auditor.txt

echo "[2/7] Applying retention cleanup..."
python app/retention_cleaner.py ||
  echo "WARNING: retention cleanup failed"

echo "[3/7] Starting cell_00 reader..."
start_process \
  python -u app/cell_00_seedlink_reader.py

echo "[4/7] Starting automatic cell readers..."

for inventory in config/auto_cell_*_inventory.json; do
  [[ -f "$inventory" ]] || continue

  filename="$(basename "$inventory")"
  cell_id="${filename%_inventory.json}"

  echo "Starting ${cell_id}"

  start_process \
    python -u app/auto_cell_seedlink_reader.py \
    "$inventory" \
    "runtime/${cell_id}_state.json"
done

echo "[5/7] Starting periodic discovery..."

(
  while true; do
    echo "=============================================="
    echo "SeedLink review: $(date -u)"
    echo "=============================================="

    python -u app/seedlink_discovery.py ||
      echo "WARNING: SeedLink discovery failed"

    echo "Waiting 15 minutes for the next review..."
    sleep 900
  done
) &

children+=("$!")

echo "[6/7] Starting sensor auditor..."
start_process \
  python -u app/sensor_auditor.py

echo "[7/7] Starting HTTP server on port 5050..."

python -m py_compile \
  app/plain_python_server.py \
  app/public_api_v1.py \
  app/telegram_notice.py

start_process \
  python -u app/plain_python_server.py

echo
echo "Cuyum processes started."

# El contenedor se considera fallido si muere cualquiera
# de sus procesos principales.
wait -n "${children[@]}"

echo "ERROR: a Cuyum process stopped unexpectedly."
exit 1
