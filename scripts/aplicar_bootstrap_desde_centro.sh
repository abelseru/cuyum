#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "=============================================="
echo "        CUYUM - APLICAR BOOTSTRAP"
echo "=============================================="
echo
echo "Centro usado:"
cat config/system_center.json | python3 -m json.tool
echo

python3 app/cuyum_bootstrap_world.py --preview --plan

SENSOR_COUNT=$(python3 -c '
import json
from pathlib import Path
p = Path("runtime/bootstrap_preview/candidate_inventory.preview.json")
if not p.exists():
    print(0)
else:
    data = json.loads(p.read_text(encoding="utf-8"))
    print(len(data.get("sensores", [])))
')

if [ "$SENSOR_COUNT" -eq 0 ]; then
    echo
    echo "[bloqueado] El preview no tiene sensores."
    echo "No se aplica para evitar dejar Cuyum sin inventario."
    echo
    echo "Revisá:"
    echo "- config/system_center.json"
    echo "- config/seedlink_station_catalog.json"
    exit 1
fi

echo
echo "Sensores en preview: $SENSOR_COUNT"
echo "Aplicando..."

python3 app/cuyum_bootstrap_world.py --preview --apply

echo
echo "Aplicado. Reiniciá Cuyum para usar el inventario nuevo:"
echo "./stop_cuyum_v1_2.sh"
echo "./start_cuyum_v1_2.sh"
echo
echo "Luego verificá:"
echo "sleep 45"
echo "scripts/ver_multicelda_v1_2.sh"
