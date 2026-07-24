from pathlib import Path
import os
import subprocess

ROOT = Path(".").resolve()

IGNORE_DIRS = {
    "venv", ".git", "__pycache__", ".pytest_cache",
    "laboratorio/cache_python", "data/runtime"
}

ACTIVE_NAMES = {
    "servidor_json_seedlink.py",
    "public_live.py",
    "multicell_fusion.py",
    "event_journal.py",
    "retention_cleaner.py",
    "sensor_auditor.py",
    "auto_cell_reader_seedlink.py",
    "zona_grupo_01_seedlink_adaptativo_v2.py",
    "descubridor_seedlink.py",
    "generar_inventory_auto_cell_01.py",
    "inventario_candidatos.json",
    "ejecutar_auto_celdas.sh",
    "auto_inventory_cells.json",
    "cuyum_auto_cells.py",
    "sensor_geo_overrides.json",
    "iniciar_cuyum_visible_v1_2.sh",
    "detener_cuyum_v1_2.sh",
    "ver_multicelda_v1_2.sh",
    "arrancar_sistema_v1_2.sh",
    "descubridor_periodico.sh",
}

ACTIVE_DIRS = {
    "templates",
    "static",
    "config",
    "docs",
    "tools",
}

def should_ignore(path: Path) -> bool:
    parts = set(path.parts)
    return any(d in parts for d in IGNORE_DIRS)

def line_count(path: Path) -> int:
    try:
        return sum(1 for _ in path.open("r", encoding="utf-8", errors="ignore"))
    except Exception:
        return 0

def classify(path: Path) -> str:
    rel = path.relative_to(ROOT)
    top = rel.parts[0]

    if should_ignore(rel):
        return "ignored"

    if path.name in ACTIVE_NAMES:
        return "active_core_or_script"

    if top in ACTIVE_DIRS:
        return "active_support"

    if top.startswith("backups") or top in {"archive", "backups_v1_2b_english_core"}:
        return "migration_backup"

    if top in {"laboratorio", "lab"}:
        return "laboratory"

    if path.suffix in {".jsonl", ".log"} or path.name.startswith("logs_"):
        return "runtime_log"

    if path.name.endswith(".bak") or path.name.endswith(".old"):
        return "backup_file"

    if path.suffix in {".pyc"}:
        return "discardable_cache"

    if path.suffix in {".py", ".sh", ".json", ".txt", ".md"}:
        return "needs_review"

    return "other"

files = []
for path in ROOT.rglob("*"):
    if path.is_dir():
        continue
    rel = path.relative_to(ROOT)
    if should_ignore(rel):
        continue

    stat = path.stat()
    files.append({
        "path": str(rel),
        "class": classify(path),
        "suffix": path.suffix,
        "size_kb": round(stat.st_size / 1024, 1),
        "lines": line_count(path) if path.suffix in {".py", ".sh", ".txt", ".md", ".json"} else 0,
    })

files.sort(key=lambda x: (x["class"], x["path"]))

report = []
report.append("# Cuyum v1.2 - file audit\n")
report.append("Generated locally. No files were moved or deleted.\n\n")

classes = sorted(set(f["class"] for f in files))
for cls in classes:
    group = [f for f in files if f["class"] == cls]
    total_kb = sum(f["size_kb"] for f in group)
    report.append(f"## {cls}\n\n")
    report.append(f"Files: {len(group)} | Approx size: {total_kb:.1f} KB\n\n")
    report.append("| file | size KB | lines |\n")
    report.append("|---|---:|---:|\n")
    for f in group:
        report.append(f"| `{f['path']}` | {f['size_kb']} | {f['lines']} |\n")
    report.append("\n")

Path("REPORTE_ARCHIVOS_V1_2.md").write_text("".join(report), encoding="utf-8")
print("Written: REPORTE_ARCHIVOS_V1_2.md")
