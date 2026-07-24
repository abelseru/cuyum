# Cuyum v1.2b - Local cell reader English-core identifier migration

Date: 2026-07-16T11:33:55
Mode: apply
Changed: True

## Scope

This migration touches only:

- `zona_grupo_01_seedlink_adaptativo_v2.py`

## Rule

Only Python identifiers are renamed in this step. JSON keys and public strings are preserved for compatibility.

## Backup

- `backups_v1_2b_english_core/zona_grupo_01_seedlink_adaptativo_v2.py.20260716_113355.bak`

## Identifier replacements

- `cargar_inventario` → `load_inventory`: 2
- `calcular_calidad_red` → `calculate_network_quality`: 2
- `nivel_por_evento` → `event_level_from_signals`: 2
- `clave_sensor_cfg` → `sensor_config_key`: 2
- `LectorSeedLinkAdaptativo` → `AdaptiveSeedLinkReader`: 2
- `servidor` → `server`: 5
- `sensores` → `sensors`: 14
- `inventario` → `inventory`: 5
- `calidad_red` → `network_quality`: 7
- `estado_sensores` → `sensor_states`: 9
- `mapa_sensores` → `sensor_map`: 4
- `estaciones_confirmando` → `confirming_stations`: 6
- `hay_flag_fuerte_anticipacion` → `has_strong_early_signal`: 5
- `flag_fuerte_crudo` → `raw_strong_flag`: 2
- `flag_fuerte` → `strong_flag`: 4
- `puede_disparar` → `can_trigger`: 4
- `cantidad` → `count`: 5
- `clave` → `key`: 26
- `calibrados` → `calibrated`: 3
- `total_activos` → `total_active`: 5
- `base_sensor` → `sensor_baseline`: 5
- `FACTOR_FLAG_FUERTE` → `STRONG_FLAG_FACTOR`: 2

## Text replacements

- `Sensores cargados:`: 1

## Post-checks

Run:

```bash
python3 -m py_compile zona_grupo_01_seedlink_adaptativo_v2.py
./iniciar_cuyum_visible_v1_2.sh
./ver_multicelda_v1_2.sh
```
