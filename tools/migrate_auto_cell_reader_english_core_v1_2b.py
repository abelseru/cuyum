#!/usr/bin/env python3
"""
Cuyum v1.2b - English-core migration, block 1

Scope:
- Migrates only auto_cell_reader_seedlink.py internal Spanish identifiers to English.
- Keeps temporary JSON compatibility by writing old Spanish keys AND new English keys.
- Creates a backup before changing anything.
- Does not touch the local cell reader, fusion, public API, web UI, ESP32, or runtime files.

Usage:
  cd ~/cuyum_v_1_2
  python3 tools/migrate_auto_cell_reader_english_core_v1_2b.py --dry-run
  python3 tools/migrate_auto_cell_reader_english_core_v1_2b.py --apply
"""

from __future__ import annotations

import argparse
import difflib
import py_compile
import shutil
from datetime import datetime
from pathlib import Path

TARGET = Path("auto_cell_reader_seedlink.py")
BACKUP_DIR = Path("backups_v1_2b_english_core")
REPORT = Path("MIGRATION_AUTO_CELL_READER_ENGLISH_CORE_V1_2B.md")

# Ordered replacements: longer / more specific first.
REPLACEMENTS = [
    # Function and local variable names
    ("cargar_inventario", "load_inventory"),
    ("calcular_calidad_red", "calculate_network_quality"),
    ("clasificar_estado", "classify_state"),
    ("clave_sensor_cfg", "sensor_config_key"),
    ("estado_base", "base_state"),
    ("publicar", "publish"),
    ("estado_sensores", "sensor_states"),
    ("flags_recientes", "recent_flags"),
    ("sensores", "sensors"),
    ("servidor", "server"),
    ("inventario", "inventory"),
    ("calidad", "quality"),
    ("calibrados", "calibrated"),
    ("cantidad", "count"),
    ("fuerte", "strong"),
    ("flag_fuerte", "strong_flag"),
    ("FACTOR_FLAG_FUERTE", "STRONG_FLAG_FACTOR"),
    ("FACTOR_FLAG", "FLAG_FACTOR"),
    ("VENTANA_SEGUNDOS", "WINDOW_SECONDS"),
    ("MIN_BASE", "BASELINE_MIN"),
    ("clave", "key"),
    ("energia", "energy"),
    ("magnitud", "magnitude"),
    ("latencia", "latency"),
    ("base_sensor", "sensor_baseline"),
    ("prioridad", "priority"),
    ("estaciones_confirmando_lista", "confirming_station_list"),
    ("estaciones_confirmando", "confirming_stations"),
    ("observacion_externa_fuerte", "external_strong_observation"),
    ("observacion_externa", "external_observation"),
]

# Public/compatibility key additions. These are intentionally simple text patches
# applied after the identifier replacements. They keep legacy Spanish keys for
# current consumers while adding English keys for v1.2b.
COMPAT_PATCHES = [
    (
        "'active_sensors': total,\n        'calibrated_sensors': len(calibrated),\n        'network_state': state,",
        "'active_sensors': total,\n        'calibrated_sensors': len(calibrated),\n        'network_state': state,\n        # Temporary compatibility keys for modules not migrated yet.\n        'sensores_activos': total,\n        'sensores_calibrados': len(calibrated),\n        'estado': state,",
    ),
    (
        "'total_sensors': len(self.sensors),\n            'active_sensors': quality['active_sensors'],\n            'calibrated_sensors': quality['calibrated_sensors'],\n            'confirming_stations': len(self.recent_flags),\n            'confirming_station_list': list(self.recent_flags.keys()),\n            'ratio_max': max([x.get('ratio', 0) for x in self.recent_flags.values()] or [0]),\n            'sensors': self.sensor_states",
        "'total_sensors': len(self.sensors),\n            'active_sensors': quality['active_sensors'],\n            'calibrated_sensors': quality['calibrated_sensors'],\n            'confirming_stations': len(self.recent_flags),\n            'confirming_station_list': list(self.recent_flags.keys()),\n            'ratio_max': max([x.get('ratio', 0) for x in self.recent_flags.values()] or [0]),\n            'sensors': self.sensor_states,\n            # Temporary compatibility keys for modules not migrated yet.\n            'sensores_totales': len(self.sensors),\n            'sensores_activos': quality['active_sensors'],\n            'sensores_calibrados': quality['calibrated_sensors'],\n            'estaciones_confirmando': len(self.recent_flags),\n            'estaciones_confirmando_lista': list(self.recent_flags.keys()),\n            'sensores': self.sensor_states",
    ),
]

# Some string keys must remain public/legacy, but we add English aliases nearby where easy.
LEGACY_KEY_COMMENT = "# NOTE: Spanish keys below are temporary compatibility aliases for v1.1/v1.2 consumers."


def apply_replacements(text: str) -> str:
    for old, new in REPLACEMENTS:
        text = text.replace(old, new)
    for old, new in COMPAT_PATCHES:
        if old in text:
            text = text.replace(old, new)
    return text


def make_report(before: str, after: str, changed: bool, dry_run: bool) -> str:
    now = datetime.now().isoformat(timespec="seconds")
    diff = "\n".join(
        difflib.unified_diff(
            before.splitlines(),
            after.splitlines(),
            fromfile="auto_cell_reader_seedlink.py.before",
            tofile="auto_cell_reader_seedlink.py.after",
            lineterm="",
        )
    )
    if len(diff) > 18000:
        diff = diff[:18000] + "\n\n[diff truncated]\n"
    mode = "dry-run" if dry_run else "apply"
    return f"""# Cuyum v1.2b - Auto cell reader English-core migration

Date: {now}
Mode: {mode}
Changed: {changed}

## Scope

This migration touches only:

- `auto_cell_reader_seedlink.py`

## Rule

Internal code moves to English identifiers. Temporary Spanish compatibility keys are preserved where current modules still consume them.

## Backup

When applied, the original file is copied into:

- `{BACKUP_DIR}/auto_cell_reader_seedlink.py.<timestamp>.bak`

## Next validation

```bash
cd ~/cuyum_v_1_2
python3 -m py_compile auto_cell_reader_seedlink.py
./detener_cuyum_v1_2.sh
./iniciar_cuyum_visible_v1_2.sh
./ver_multicelda_v1_2.sh
```

## Diff

```diff
{diff}
```
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if args.dry_run == args.apply:
        raise SystemExit("Use exactly one mode: --dry-run or --apply")

    if not TARGET.exists():
        raise SystemExit(f"ERROR: {TARGET} not found. Run from Cuyum project root.")

    before = TARGET.read_text(encoding="utf-8")
    after = apply_replacements(before)
    changed = before != after

    report = make_report(before, after, changed, args.dry_run)
    REPORT.write_text(report, encoding="utf-8")

    if args.dry_run:
        print(f"[dry-run] changed={changed}")
        print(f"[dry-run] report: {REPORT}")
        return 0

    if not changed:
        print("[apply] no changes needed")
        print(f"[apply] report: {REPORT}")
        return 0

    BACKUP_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = BACKUP_DIR / f"auto_cell_reader_seedlink.py.{stamp}.bak"
    shutil.copy2(TARGET, backup)
    TARGET.write_text(after, encoding="utf-8")

    try:
        py_compile.compile(str(TARGET), doraise=True)
    except Exception as exc:
        shutil.copy2(backup, TARGET)
        raise SystemExit(f"ERROR: py_compile failed. File restored from {backup}. Details: {exc}")

    print(f"[ok] updated: {TARGET}")
    print(f"[ok] backup: {backup}")
    print(f"[ok] report: {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
