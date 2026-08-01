#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 3 ]; then
  echo "Usage:"
  echo "  ./scripts/cuyum_recenter_live.sh \"Center name\" LAT LON"
  echo
  echo "Examples:"
  echo "  ./scripts/cuyum_recenter_live.sh \"Mendoza\" -32.8895 -68.8458"
  echo "  ./scripts/cuyum_recenter_live.sh \"San Juan\" -31.5375 -68.5364"
  echo "  ./scripts/cuyum_recenter_live.sh \"Caracas\" 10.4806 -66.9036"
  exit 1
fi

LABEL="$1"
LAT="$2"
LON="$3"

cd "$(dirname "$0")/.."

PY="./venv/bin/python"

if [ ! -x "$PY" ]; then
  echo "ERROR: Python executable not found: $PY"
  exit 1
fi

echo "=============================================="
echo " CUYUM - RECENTER LIVE"
echo "=============================================="
echo "Center: $LABEL"
echo "Lat:    $LAT"
echo "Lon:    $LON"
echo

echo "[1/8] Stopping Cuyum..."
if docker compose ps >/dev/null 2>&1; then
    docker compose down || true
else
    sudo docker compose down || true
fi

echo
echo "[2/8] Resetting previous live state..."
rm -f runtime/auto_cell_*_state.json
rm -f runtime/cell_00_state.json
rm -f runtime/live_inventory_organizer_report.json
rm -f runtime/live_inventory_organizer_report.txt
rm -f config/auto_cell_*_inventory.json

mkdir -p config runtime

echo
echo "[3/8] Writing config/system_center.json..."
"$PY" - "$LABEL" "$LAT" "$LON" <<'PY'
import json
import sys
from pathlib import Path
from datetime import datetime

label = sys.argv[1]
lat = float(sys.argv[2])
lon = float(sys.argv[3])

data = {
    "label": label,
    "lat": lat,
    "lon": lon,
    "updated_at": datetime.now().isoformat(),
    "updated_by": "cuyum_recenter_live"
}

Path("config/system_center.json").write_text(
    json.dumps(data, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print(json.dumps(data, ensure_ascii=False, indent=2))
PY

echo
echo "[4/8] Rebuilding regional station catalog..."
"$PY" app/regional_station_catalog_builder.py \
  --label "$LABEL" \
  --lat "$LAT" \
  --lon "$LON" \
  --apply

echo
echo "[5/8] Rebuilding complete candidate inventory..."
"$PY" app/regional_candidate_inventory_builder.py --apply

echo
echo "[6/8] Organizing live inventory with hard limits..."
"$PY" app/live_inventory_organizer.py \
  --local-max-km 200 \
  --local-max 4 \
  --zone-max 4 \
  --sensors-per-zone 3 \
  --absolute-max 18

echo
echo "=== Organizer summary ==="
cat runtime/live_inventory_organizer_report.txt || true

echo
echo "[7/8] Starting Cuyum..."
if docker compose ps >/dev/null 2>&1; then
    docker compose up -d --build
else
    sudo docker compose up -d --build
fi

echo
echo "[8/8] Waiting for initial stabilization..."
sleep 30

echo
echo "=== Current /json state ==="
"$PY" - <<'PYJSON' | sed -n '1,140p'
import json
import urllib.request

with urllib.request.urlopen(
    "http://127.0.0.1:5050/json",
    timeout=10,
) as response:
    data = json.load(response)

print(json.dumps(data, ensure_ascii=False, indent=2))
PYJSON

echo
echo "=============================================="
echo " RECENTERING COMPLETE"
echo "=============================================="
echo "Open:"
echo "  http://127.0.0.1:5050/app"
