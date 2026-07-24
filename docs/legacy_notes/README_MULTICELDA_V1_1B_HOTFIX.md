# Cuyum v1.1b - Hotfix multicelda

Este parche corrige la fusión multicelda y cambia la filosofía de clasificación de células.

## Nueva escala

- `strong_cell`: 6 o más sensores vivos.
- `good_cell`: 4 o 5 sensores vivos.
- `minimal_cell`: 2 o 3 sensores vivos.
- `single_station`: 1 sensor vivo.
- `stale_cell` / `blind_zone`: sin datos recientes o sin cobertura.

## Regla prudente

Una célula mínima no se ignora, pero tampoco dispara alarma fuerte sola.
Puede elevar vigilancia y ayudar a confirmar.

## ESP32

El endpoint viejo se mantiene:

```text
/api/node/poll?node_id=node_01
```

El sketch actual no debería romperse porque se conservan los campos viejos:

- `nivel`
- `mensaje`
- `calidad_red`
- `sensores_activos`
- `sensores_calibrados`
- `sonar`
- `buzzer_segundos`
- `led_nivel`

También se agregan campos multicelda para el próximo sketch:

- `network_mode`
- `network_label`
- `cells_active`
- `strong_cells`
- `good_cells`
- `minimal_cells`
- `single_station_cells`
- `cell_00_class`
- `auto_cell_01_class`
- `auto_cell_01_aviso_util`

## Prueba

```bash
cd ~/cuyum_v_1_1
./detener_cuyum_v1_1.sh
./iniciar_cuyum_visible_v1_1.sh
```

En otra terminal:

```bash
cd ~/cuyum_v_1_1
./ver_multicelda_v1_1.sh
curl "http://127.0.0.1:5000/api/node/poll?node_id=node_01"
```
