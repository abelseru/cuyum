from pathlib import Path
import shutil
from datetime import datetime

ROOT = Path(".").resolve()

MOVES = []

def add(patterns, target_dir):
    for pattern in patterns:
        for path in ROOT.glob(pattern):
            if path.is_file():
                MOVES.append((path, ROOT / target_dir / path.name))

# Documentation and migration notes
add([
    "README_*.md",
    "README_*.txt",
], "docs/legacy_notes")

add([
    "MIGRATION_*.md",
    "AUDITORIA_*.md",
    "REPORTE_LIMPIEZA_V1_2.md",
], "docs/migration")

# Old generated reports
add([
    "auto_cells_report.*",
    "cell02_confirm_v4d_report.*",
    "cell_candidates_report*",
    "seedlink_probe_*_report.*",
    "cuyum_patch_diff.txt",
], "laboratorio/reportes_antiguos")

# Old test/probe/dry-run scripts
add([
    "ejecutar_*.sh",
    "iniciar_auto_cell_01_prueba.sh",
    "detener_auto_cell_01_prueba.sh",
    "ver_estado_auto_cell_01.sh",
], "laboratorio/scripts_antiguos")

# Legacy v1.1 or pre-v1.2 wrappers
add([
    "arrancar_sistema.sh",
    "detener_cuyum.sh",
    "detener_cuyum_v1_1.sh",
    "iniciar_cuyum_visible.sh",
    "iniciar_cuyum_visible_v1_1.sh",
    "ver_multicelda_v1_1.sh",
    "zona_grupo_01_seedlink_adaptativo.py",
    "README_CUYUM_V1_1*.md",
    "README_CUYUM_V1_1*.txt",
    "README_MULTICELDA_V1_1*.md",
], "laboratorio/legacy_v1_1")

# Old configs/inventories/reports not used by the current startup
add([
    "auto_inventory_cells.json",
    "config_cells_v1_1_dryrun_v2.json",
    "config_cuyum_v1_1_dryrun.json",
    "cuyum_data_sources.json",
    "cuyum_runtime_cells.json",
    "cuyum_zones_setup.json",
    "inventario_candidatos.json",
    "inventory_cell_02_live_v4d.json",
    "inventory_cells_v4*.json",
], "laboratorio/configs_antiguas")

# Migration helper scripts already used
add([
    "cuyum_v1_2_aislar_rutas_operativas.sh",
    "cuyum_v1_2_ordenar_y_auditar_nombres.sh",
    "cuyum_v1_2_ordenar_y_cuarentenar.sh",
], "tools/migration")

# Never move these yet
KEEP = {
    "ESTADO_ACTUAL_V1_2.md",
    "language.md",
    "config_cuyum.json",
    "cuyum_auto_config.json",
    "sensor_catalog.json",
    "estado_global.json",
    "estado_global_completo.json",
    "estado_grupo_01.json",
    "estado_grupo_01_completo.json",
    "estado_grupo_01_seedlink.json",
    "event_journal_state.json",
    "inventory_auto_cell_01.json",
    "ejecutar_auto_celdas.sh",
    "state_auto_cell_01.json",
}

manifest = []
manifest.append("# Cuyum v1.2 quarantine manifest\n\n")
manifest.append(f"Generated: {datetime.now().isoformat(timespec='seconds')}\n\n")
manifest.append("No files were deleted.\n\n")
manifest.append("| source | target |\n")
manifest.append("|---|---|\n")

seen = set()
count = 0

for source, target in MOVES:
    rel = source.relative_to(ROOT)

    if source.name in KEEP:
        continue

    if source in seen:
        continue
    seen.add(source)

    if not source.exists():
        continue

    target.parent.mkdir(parents=True, exist_ok=True)

    # Avoid overwriting
    final_target = target
    if final_target.exists():
        final_target = target.with_name(target.stem + ".quarantine_" + datetime.now().strftime("%Y%m%d_%H%M%S") + target.suffix)

    shutil.move(str(source), str(final_target))
    manifest.append(f"| `{rel}` | `{final_target.relative_to(ROOT)}` |\n")
    count += 1

Path("REPORTE_CUARENTENA_V1_2.md").write_text("".join(manifest), encoding="utf-8")
print(f"Moved files: {count}")
print("Written: REPORTE_CUARENTENA_V1_2.md")
