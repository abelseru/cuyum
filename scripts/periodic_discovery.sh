#!/bin/bash

cd ~/cuyum_v_1_2
source venv/bin/activate

while true
do
    echo "=============================================="
    echo "Revision SeedLink: $(date -u)"
    echo "=============================================="

    python -u app/seedlink_discovery.py

    echo "Esperando 15 minutos para la próxima revisión..."
    echo ""
    sleep 900
done
