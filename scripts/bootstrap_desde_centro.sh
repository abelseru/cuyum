#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "=============================================="
echo "        CUYUM - BOOTSTRAP DESDE CENTRO"
echo "=============================================="
echo
echo "Centro usado:"
cat config/system_center.json | python3 -m json.tool
echo

python3 app/cuyum_bootstrap_world.py --preview --plan

echo
echo "Preview generado en:"
echo "- runtime/bootstrap_preview/README.txt"
echo "- runtime/bootstrap_preview/candidate_inventory.preview.json"
echo
echo "Para aplicar el preview:"
echo "python3 app/cuyum_bootstrap_world.py --preview --apply"
