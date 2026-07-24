#!/bin/bash
clear
echo "=============================================="
echo "        CUYUM v1.1 - AUTO CELDAS"
echo "=============================================="
echo "No modifica el sistema vivo."
echo "Construye auto_cells_report.txt/json y config/auto_inventory_cells.json"
echo ""
cd /home/usuario/cuyum_v_1_1 || {
  echo "ERROR: no existe /home/usuario/cuyum_v_1_1"
  read -p "Presione ENTER para cerrar..."
  exit 1
}
source venv/bin/activate
python app/cuyum_auto_cells.py

echo ""
echo "=============================================="
echo "        REPORTE AUTO CELDAS"
echo "=============================================="
cat auto_cells_report.txt 2>/dev/null || echo "No se genero auto_cells_report.txt"
echo ""
read -p "Presione ENTER para cerrar..."
