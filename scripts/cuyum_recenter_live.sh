#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 3 ]; then
  echo "Usage:"
  echo "  ./scripts/cuyum_recenter_live.sh \"Center name\" LAT LON"
  echo
  echo "Examples:"
  echo "  ./scripts/cuyum_recenter_live.sh \"Mendoza\" -32.8895 -68.8458"
  echo "  ./scripts/cuyum_recenter_live.sh \"San Juan\" -31.5375 -68.5364"
  echo "  ./scripts/cuyum_recenter_live.sh \"CDMX\" 19.4326 -99.1332"
  exit 1
fi

LABEL="$1"
LAT="$2"
LON="$3"

cd "$(dirname "$0")/.."

if docker compose version >/dev/null 2>&1; then
  DC=(docker compose)
elif sudo docker compose version >/dev/null 2>&1; then
  DC=(sudo docker compose)
else
  echo "ERROR: Docker Compose is not available."
  exit 1
fi

echo "=============================================="
echo " CUYUM - RECENTER LIVE (DOCKER)"
echo "=============================================="
echo "Center: $LABEL"
echo "Lat:    $LAT"
echo "Lon:    $LON"
echo

echo "[1/9] Stopping Cuyum..."
"${DC[@]}" down

echo
echo "[2/9] Building the Cuyum image..."
"${DC[@]}" build cuyum

echo
echo "[3/9] Resetting previous live state..."
rm -f runtime/auto_cell_*_state.json
rm -f runtime/cell_00_state.json
rm -f runtime/live_inventory_organizer_report.json
rm -f runtime/live_inventory_organizer_report.txt
rm -f config/auto_cell_*_inventory.json
mkdir -p config runtime

echo
echo "[4/9] Writing config/system_center.json..."
"${DC[@]}" run --rm --no-deps --entrypoint python cuyum \
  - "$LABEL" "$LAT" "$LON" <<'PY'
import json
import sys
from datetime import datetime
from pathlib import Path

label = sys.argv[1]
lat = float(sys.argv[2])
lon = float(sys.argv[3])

data = {
    "label": label,
    "lat": lat,
    "lon": lon,
    "updated_at": datetime.now().isoformat(),
    "updated_by": "cuyum_recenter_live",
}

Path("config/system_center.json").write_text(
    json.dumps(data, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

print(json.dumps(data, ensure_ascii=False, indent=2))
PY

echo
echo "[5/9] Rebuilding regional station catalog..."
"${DC[@]}" run --rm --no-deps --entrypoint python cuyum \
  app/regional_station_catalog_builder.py \
  --label "$LABEL" \
  --lat "$LAT" \
  --lon "$LON" \
  --apply

echo
echo "[6/9] Rebuilding complete candidate inventory..."
"${DC[@]}" run --rm --no-deps --entrypoint python cuyum \
  app/regional_candidate_inventory_builder.py --apply

echo
echo "[7/9] Organizing live inventory with hard limits..."
"${DC[@]}" run --rm --no-deps --entrypoint python cuyum \
  app/live_inventory_organizer.py \
  --local-max-km 200 \
  --local-max 4 \
  --zone-max 4 \
  --sensors-per-zone 3 \
  --absolute-max 18

echo
echo "=== Organizer summary ==="
cat runtime/live_inventory_organizer_report.txt || true

echo
echo "[8/9] Starting Cuyum..."
"${DC[@]}" up -d

echo
echo "[9/9] Waiting for initial stabilization..."
sleep 30

echo
echo "=== Current /json state ==="
"${DC[@]}" exec -T cuyum python - <<'PYJSON' | sed -n '1,140p'
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
echo "  https://cuyum.ar/app"
