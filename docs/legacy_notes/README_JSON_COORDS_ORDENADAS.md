# Hotfix JSON público: coordenadas agrupadas

Este parche ordena la salida pública para que las coordenadas aparezcan juntas como `coords`.

## /api/public/events

Cada evento de sensor compacto muestra:

```json
"sensor": {
  "id": "C1.MT08.BHZ",
  "name": "Bocatoma Colorado",
  "station": "MT08",
  "locality": "Bocatoma Colorado",
  "coords": {
    "lat": -33.4052,
    "lon": -70.1334
  },
  "location": {
    "approx": true,
    "source": "visualizacion_publica_aproximada"
  }
}
```

## /api/public/live

Los sensores del estado vivo también agregan `coords` y `location`, manteniendo `lat` y `lon` planos para no romper el mapa existente.
