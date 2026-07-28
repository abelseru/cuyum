#!/bin/bash

cd ~/cuyum_v_1_2 || exit 1
source venv/bin/activate

while true
do
    echo "=============================================="
    echo "SeedLink review: $(date -u)"
    echo "=============================================="

    python -u app/seedlink_discovery.py

    echo "Waiting 15 minutes for the next review..."
    echo ""
    sleep 900
done
