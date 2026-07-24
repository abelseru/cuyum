#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

echo "=============================================="
echo "        CUYUM v1.2"
echo "=============================================="
echo

if [ ! -d "venv" ]; then
  echo "ERROR: venv directory not found."
  exit 1
fi

source venv/bin/activate

echo "[1/8] Stopping previous Cuyum..."
pkill -f app/plain_python_server.py 2>/dev/null || true
pkill -f app/cell_00_seedlink_reader.py 2>/dev/null || true
pkill -f app/auto_cell_seedlink_reader.py 2>/dev/null || true
pkill -f periodic_discovery.sh 2>/dev/null || true
pkill -f app/seedlink_discovery.py 2>/dev/null || true
pkill -f app/sensor_auditor.py 2>/dev/null || true
sleep 2

echo "[2/8] Cleaning logs..."
mkdir -p runtime_logs
: > runtime_logs/logs_cuyum_server.txt
: > runtime_logs/logs_lector.txt
: > runtime_logs/logs_auto_cell_01.txt
: > runtime_logs/logs_descubridor.txt
: > runtime_logs/logs_sensor_auditor.txt

echo "[3/8] Applying retention cleanup..."
if [ -f app/retention_cleaner.py ]; then
  python app/retention_cleaner.py || echo "WARNING: retention cleanup failed"
fi

echo "[4/9] Preparing auto cell inventories..."
echo "Using existing config/auto_cell_*_inventory.json microcell inventories"
ls config/auto_cell_*_inventory.json 2>/dev/null || echo "WARNING: no auto microcell inventories found"

echo "[5/9] Updating regional preview for current center..."
if [ -f app/regional_auto_preview.py ]; then
  CENTER_VARS=$(./venv/bin/python - <<'PYCENTER'
import json, shlex
from pathlib import Path

p = Path("config/system_center.json")
data = json.loads(p.read_text(encoding="utf-8"))

lat = data.get("lat")
lon = data.get("lon")
label = data.get("label") or data.get("name") or "Centro actual"

if lat is None or lon is None:
    raise SystemExit("system_center.json without lat/lon")

print("CENTER_LAT=" + shlex.quote(str(lat)))
print("CENTER_LON=" + shlex.quote(str(lon)))
print("CENTER_LABEL=" + shlex.quote(str(label)))
PYCENTER
)
  eval "$CENTER_VARS"

  REGIONAL_PREVIEW_DURATION="${REGIONAL_PREVIEW_DURATION:-45}"
  REGIONAL_PREVIEW_MAX_SENSORS="${REGIONAL_PREVIEW_MAX_SENSORS:-120}"
  REGIONAL_PREVIEW_MAX_KM="${REGIONAL_PREVIEW_MAX_KM:-800}"

  mkdir -p runtime/bootstrap_preview runtime_logs
  rm -f runtime/regional_auto_preview_summary.json
  rm -f runtime/regional_auto_preview_summary.txt
  rm -f runtime/seedlink_preview_liveness_result.json
  rm -f runtime/seedlink_preview_liveness_result.txt
  rm -f runtime/bootstrap_preview/candidate_inventory.alive.preview.json

  (
    echo "Regional preview started: $(date -Is)"
    echo "Center: $CENTER_LABEL lat=$CENTER_LAT lon=$CENTER_LON"
    echo "Duration: $REGIONAL_PREVIEW_DURATION seconds"
    echo "Max sensors: $REGIONAL_PREVIEW_MAX_SENSORS"
    echo "Max km: $REGIONAL_PREVIEW_MAX_KM"
    echo

    ./venv/bin/python app/regional_auto_preview.py \
      --lat "$CENTER_LAT" \
      --lon "$CENTER_LON" \
      --label "$CENTER_LABEL" \
      --duration "$REGIONAL_PREVIEW_DURATION" \
      --max-sensors "$REGIONAL_PREVIEW_MAX_SENSORS" \
      --max-km "$REGIONAL_PREVIEW_MAX_KM" \
      --provider IRIS

    echo
    echo "Regional preview finished: $(date -Is)"
  ) > runtime_logs/logs_regional_preview.txt 2>&1 &

  echo "Regional preview updating in background."
  echo "Log: runtime_logs/logs_regional_preview.txt"
else
  echo "WARNING: app/regional_auto_preview.py not found"
fi

echo "[6/9] Starting cell_00 reader..."
python -u app/cell_00_seedlink_reader.py > runtime_logs/logs_lector.txt 2>&1 &
sleep 2

echo "[7/9] Starting auto cell readers..."
for inv in config/auto_cell_*_inventory.json; do
  [ -f "$inv" ] || continue
  base=$(basename "$inv")
  cid=${base%_inventory.json}
  echo "Starting $cid"
  python -u app/auto_cell_seedlink_reader.py "$inv" "runtime/${cid}_state.json" > "runtime_logs/logs_${cid}.txt" 2>&1 &
done
sleep 2

echo "[8/9] Starting discovery and auditor..."
if [ -f scripts/periodic_discovery.sh ]; then
  ./scripts/periodic_discovery.sh > runtime_logs/logs_descubridor.txt 2>&1 &
else
  echo "WARNING: scripts/periodic_discovery.sh not found"
fi

if [ -f app/sensor_auditor.py ]; then
  python -u app/sensor_auditor.py > runtime_logs/logs_sensor_auditor.txt 2>&1 &
else
  echo "WARNING: app/sensor_auditor.py not found"
fi
sleep 2

echo "[9/9] Starting Cuyum on port 5050..."
python3 -m py_compile app/plain_python_server.py app/public_api_v1.py
./venv/bin/python -u app/plain_python_server.py > runtime_logs/logs_cuyum_server.txt 2>&1 &
sleep 5

echo
echo "=============================================="
echo "        CUYUM"
echo "=============================================="
ps aux | grep -E "cell_00_seedlink_reader|auto_cell_seedlink_reader|periodic_discovery|seedlink_discovery|sensor_auditor|plain_python_server" | grep -v grep || true

echo
echo "=============================================="
echo "        CHECK"
echo "=============================================="

for url in \
  "http://127.0.0.1:5050/app" \
  "http://127.0.0.1:5050/json" \
  "http://127.0.0.1:5050/regional-preview" \
  "http://127.0.0.1:5050/json/regional-preview" \
  "http://127.0.0.1:5050/reg" \
  "http://127.0.0.1:5050/api/node/poll?node_id=node_01" \
  "http://127.0.0.1:5050/api/esp32/poll?node_id=node_01"
do
  code=$(python - <<PY
import urllib.request
try:
    r = urllib.request.urlopen("$url", timeout=5)
    print(r.status)
except Exception:
    print("FAIL")
PY
)
  echo "$code  $url"
done

echo
echo "Open:"
echo "http://127.0.0.1:5050/app"
echo "http://192.168.1.37:5050/app"
echo
echo "Regional preview:"
echo "http://127.0.0.1:5050/regional-preview"
echo "http://192.168.1.37:5050/regional-preview"
echo
echo "To stop Cuyum:"
echo "./stop_cuyum_v1_2.sh"
