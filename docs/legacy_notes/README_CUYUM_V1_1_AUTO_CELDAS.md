# Cuyum v1.1 - Auto-celdas

Este parche consolida el trabajo de pruebas en un modo automático inicial.

## Principio de diseño

Cuyum v1.1 toma como modo por defecto:

```json
"cell_generation": {
  "mode": "auto",
  "default": true
}
```

La zona local (`cell_00`) queda como control. Las células de anticipación se crean desde sensores que ya demostraron respirar por SeedLink.

## Regla 1

Si una zona no puede dar al menos 10 segundos útiles de aviso, no se crea como célula de anticipación. Puede existir como control/contexto, pero no como célula de alerta temprana.

El cálculo inicial es conservador:

```text
aviso útil = distancia / velocidad_s - latencia_decisión - margen
```

Valores iniciales:

```json
"assumed_s_wave_km_s": 3.5,
"decision_latency_seconds": 3,
"safety_margin_seconds": 2,
"min_effective_warning_seconds": 10
```

## Archivos principales

- `cuyum_auto_config.json`: configuración del modo automático.
- `cuyum_auto_cells.py`: construye las auto-celdas desde cachés y sensores vivos confirmados.
- `ejecutar_auto_celdas.sh`: ejecución visible.
- `auto_cells_report.txt`: reporte humano.
- `auto_cells_report.json`: reporte completo.
- `auto_inventory_cells.json`: inventario sugerido.
- `cuyum_runtime_cells.json`: forma base para futura integración.

## Importante

Este paso no modifica el sistema vivo, no toca el ESP32 y no arranca nuevas células. Solo genera propuesta automática.

Para ejecutar:

```bash
cd ~/cuyum_v_1_1
./ejecutar_auto_celdas.sh
```

