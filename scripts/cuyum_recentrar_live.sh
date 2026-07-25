#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 3 ]; then
  echo "Uso:"
  echo "  ./scripts/cuyum_recentrar_live.sh \"Nombre del centro\" LAT LON"
  echo
  echo "Ejemplos:"
  echo "  ./scripts/cuyum_recentrar_live.sh \"Mendoza\" -32.8895 -68.8458"
  echo "  ./scripts/cuyum_recentrar_live.sh \"San Juan\" -31.5375 -68.5364"
  echo "  ./scripts/cuyum_recentrar_live.sh \"Caracas\" 10.4806 -66.9036"
  exit 1
fi

LABEL="$1"
LAT="$2"
LON="$3"

cd "$(dirname "$0")/.."

PY="./venv/bin/python"

if [ ! -x "$PY" ]; then
  echo "ERROR: no encuentro $PY"
  exit 1
fi

echo "=============================================="
echo " CUYUM - RECENTRAR LIVE"
echo "=============================================="
echo "Centro: $LABEL"
echo "Lat:    $LAT"
echo "Lon:    $LON"
echo

echo "[1/9] Apagando Cuyum..."
./stop_cuyum_v1_2.sh || true

echo
echo "[2/9] Reset de estado vivo anterior..."
rm -f cuyum_runtime_cells.json
rm -f runtime/auto_cell_*_state.json
rm -f runtime/cell_00_state.json
rm -f runtime/live_inventory_organizer_report.json
rm -f runtime/live_inventory_organizer_report.txt
rm -f config/auto_cell_*_inventory.json
rm -f config/auto_inventory_cells.json

mkdir -p config runtime

echo
echo "[3/9] Escribiendo config/system_center.json..."
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
    "updated_by": "cuyum_recentrar_live"
}

Path("config/system_center.json").write_text(
    json.dumps(data, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print(json.dumps(data, ensure_ascii=False, indent=2))
PY

echo
echo "[4/9] Sincronizando cuyum_auto_config.json..."
"$PY" - "$LABEL" "$LAT" "$LON" <<'PY'
import json
import sys
from pathlib import Path
from datetime import datetime

label = sys.argv[1]
lat = float(sys.argv[2])
lon = float(sys.argv[3])

path = Path("cuyum_auto_config.json")
try:
    data = json.loads(path.read_text(encoding="utf-8"))
except Exception:
    data = {}

data["system_center"] = {
    "label": label,
    "lat": lat,
    "lon": lon,
    "updated_at": datetime.now().isoformat(),
    "updated_by": "cuyum_recentrar_live"
}

data["center_label"] = label
data["center_lat"] = lat
data["center_lon"] = lon

path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

print("cuyum_auto_config.json actualizado")
PY

echo
echo "[5/9] Reconstruyendo catálogo regional para el centro..."
"$PY" app/regional_station_catalog_builder.py \
  --label "$LABEL" \
  --lat "$LAT" \
  --lon "$LON" \
  --apply

echo
echo "[6/9] Reconstruyendo candidate_inventory completo..."
"$PY" app/regional_candidate_inventory_builder.py --apply

echo
echo "[7/9] Organizando inventario live con límites duros..."
"$PY" app/live_inventory_organizer.py \
  --local-max-km 200 \
  --local-max 4 \
  --zone-max 4 \
  --sensors-per-zone 3 \
  --absolute-max 18

echo
echo "=== Resumen del organizador ==="
cat runtime/live_inventory_organizer_report.txt || true

echo
echo "[8/9] Arrancando Cuyum..."
./start_cuyum_v1_2.sh

echo
echo "[9/9] Esperando estabilización inicial..."
sleep 30

echo
echo "=== Estado actual /json ==="
curl -s http://127.0.0.1:5050/json | "$PY" -m json.tool | sed -n '1,140p'

echo
echo "=============================================="
echo " RECENTRADO TERMINADO"
echo "=============================================="
echo "Abrir:"
echo "  http://127.0.0.1:5050/app"
