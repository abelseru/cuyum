#!/usr/bin/env python3
"""
Cuyum v1.2b - migrate local cell reader to English-core identifiers.

Scope:
- zona_grupo_01_seedlink_adaptativo_v2.py only.

This migration intentionally renames Python identifiers only.
It does NOT rename JSON keys or public/user-facing text yet, because those keys
are still consumed by multicell_fusion.py, public_live.py and ESP32 compatibility code.

Usage:
  python3 tools/migrate_local_cell_reader_identifiers_v1_2b.py --dry-run
  python3 tools/migrate_local_cell_reader_identifiers_v1_2b.py --apply
"""

from __future__ import annotations

import argparse
import datetime as _dt
import io
import shutil
import sys
import tokenize
from pathlib import Path

TARGET = Path("zona_grupo_01_seedlink_adaptativo_v2.py")
BACKUP_DIR = Path("backups_v1_2b_english_core")
REPORT = Path("MIGRATION_LOCAL_CELL_READER_IDENTIFIERS_V1_2B.md")

# Python NAME-token replacements only. Strings are left untouched on purpose.
NAME_MAP = {
    # functions
    "cargar_inventario": "load_inventory",
    "calcular_calidad_red": "calculate_network_quality",
    "nivel_por_evento": "event_level_from_signals",
    "clave_sensor_cfg": "sensor_config_key",

    # classes
    "LectorSeedLinkAdaptativo": "AdaptiveSeedLinkReader",

    # common variables
    "servidor": "server",
    "sensores": "sensors",
    "inventario": "inventory",
    "calidad_red": "network_quality",
    "estado_sensores": "sensor_states",
    "mapa_sensores": "sensor_map",
    "estaciones_confirmando": "confirming_stations",
    "hay_flag_fuerte_anticipacion": "has_strong_early_signal",
    "flag_fuerte_crudo": "raw_strong_flag",
    "flag_fuerte": "strong_flag",
    "puede_disparar": "can_trigger",
    "cantidad": "count",
    "clave": "key",
    "calibrados": "calibrated",
    "total_activos": "total_active",
    "base_sensor": "sensor_baseline",
    "estado_sensor": "sensor_state",

    # constants
    "FACTOR_FLAG_FUERTE": "STRONG_FLAG_FACTOR",
}

TEXT_REPLACEMENTS = {
    # Comments and technical console messages only. JSON/public strings are not broadly changed here.
    "# Si supera este ratio, se considera flag fuerte.": "# If this ratio is exceeded, it is considered a strong flag.",
    "Sensores cargados:": "Loaded sensors:",
}


def rename_python_names(source: str) -> tuple[str, dict[str, int]]:
    counts = {name: 0 for name in NAME_MAP}
    tokens = []
    readline = io.StringIO(source).readline

    try:
        stream = tokenize.generate_tokens(readline)
        for tok in stream:
            tok_type, tok_string, start, end, line = tok
            if tok_type == tokenize.NAME and tok_string in NAME_MAP:
                counts[tok_string] += 1
                tok = tokenize.TokenInfo(tok_type, NAME_MAP[tok_string], start, end, line)
            tokens.append(tok)
    except tokenize.TokenError as exc:
        raise RuntimeError(f"tokenize failed: {exc}") from exc

    return tokenize.untokenize(tokens), counts


def apply_text_replacements(text: str) -> tuple[str, dict[str, int]]:
    counts = {}
    for old, new in TEXT_REPLACEMENTS.items():
        n = text.count(old)
        if n:
            text = text.replace(old, new)
        counts[old] = n
    return text, counts


def write_report(mode: str, changed: bool, name_counts: dict[str, int], text_counts: dict[str, int], backup_path: Path | None) -> None:
    now = _dt.datetime.now().isoformat(timespec="seconds")
    lines = [
        "# Cuyum v1.2b - Local cell reader English-core identifier migration",
        "",
        f"Date: {now}",
        f"Mode: {mode}",
        f"Changed: {changed}",
        "",
        "## Scope",
        "",
        "This migration touches only:",
        "",
        "- `zona_grupo_01_seedlink_adaptativo_v2.py`",
        "",
        "## Rule",
        "",
        "Only Python identifiers are renamed in this step. JSON keys and public strings are preserved for compatibility.",
        "",
        "## Backup",
        "",
        f"- `{backup_path}`" if backup_path else "- Not created in dry-run mode.",
        "",
        "## Identifier replacements",
        "",
    ]

    any_name = False
    for old, new in NAME_MAP.items():
        n = name_counts.get(old, 0)
        if n:
            any_name = True
            lines.append(f"- `{old}` → `{new}`: {n}")
    if not any_name:
        lines.append("- No identifier replacements found.")

    lines += ["", "## Text replacements", ""]
    any_text = False
    for old, n in text_counts.items():
        if n:
            any_text = True
            lines.append(f"- `{old}`: {n}")
    if not any_text:
        lines.append("- No technical text replacements found.")

    lines += [
        "",
        "## Post-checks",
        "",
        "Run:",
        "",
        "```bash",
        "python3 -m py_compile zona_grupo_01_seedlink_adaptativo_v2.py",
        "./iniciar_cuyum_visible_v1_2.sh",
        "./ver_multicelda_v1_2.sh",
        "```",
        "",
    ]

    REPORT.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if args.dry_run == args.apply:
        print("Use exactly one mode: --dry-run or --apply", file=sys.stderr)
        return 2

    if not TARGET.exists():
        print(f"[error] missing target: {TARGET}", file=sys.stderr)
        return 1

    source = TARGET.read_text(encoding="utf-8")
    migrated, name_counts = rename_python_names(source)
    migrated, text_counts = apply_text_replacements(migrated)

    changed = migrated != source
    backup_path = None

    if args.apply and changed:
        BACKUP_DIR.mkdir(exist_ok=True)
        stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = BACKUP_DIR / f"{TARGET.name}.{stamp}.bak"
        shutil.copy2(TARGET, backup_path)
        TARGET.write_text(migrated, encoding="utf-8")
        print(f"[ok] updated: {TARGET}")
        print(f"[ok] backup: {backup_path}")
    elif args.apply:
        print(f"[ok] no changes needed: {TARGET}")
    else:
        print(f"[dry-run] changed={changed}")

    write_report("apply" if args.apply else "dry-run", changed, name_counts, text_counts, backup_path)
    print(f"[ok] report: {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
