#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

echo "Stopping Cuyum..."

pkill -f plain_python_server.py 2>/dev/null || true
pkill -f cell_00_seedlink_reader.py 2>/dev/null || true
pkill -f auto_cell_seedlink_reader.py 2>/dev/null || true
pkill -f periodic_discovery.sh 2>/dev/null || true
pkill -f seedlink_discovery.py 2>/dev/null || true
pkill -f sensor_auditor.py 2>/dev/null || true

sleep 2

echo
echo "Remaining processes:"
ps aux | grep -E "cell_00_seedlink_reader|auto_cell_seedlink_reader|periodic_discovery|seedlink_discovery|sensor_auditor|plain_python_server" | grep -v grep || true

echo
echo "Port 5050:"
ss -ltnp | grep 5050 || true
