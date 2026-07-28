# Cuyum v1.2 - HTTP interfaces

Default server: http://127.0.0.1:5050

## Public interfaces
- GET /app: human-facing live monitor.
- GET /json: canonical live state.
- GET /reg: recent public event records.

## Internal and device interfaces
- GET /health: basic server status.
- GET /api/node/poll?node_id=node_01: polling interface for external nodes.
- GET /api/esp32/poll?node_id=node_01: polling interface for ESP32 clients.
- GET /api/network/state: technical network state.
- GET /api/cells/<cell_id>: technical state for a specific cell.

## Contract policy
The canonical public interfaces are /app, /json and /reg.
Cuyum does not maintain parallel public aliases for the same live-state contract.

Cuyum is experimental and does not replace official seismic information.
