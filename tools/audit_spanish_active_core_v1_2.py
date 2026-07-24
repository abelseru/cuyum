from pathlib import Path
import re

FILES = [
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
    "cuyum_auto_cells.py",
    "iniciar_cuyum_visible_v1_2.sh",
    "detener_cuyum_v1_2.sh",
    "ver_multicelda_v1_2.sh",
    "arrancar_sistema_v1_2.sh",
]

PATTERNS = [
    "sensores",
    "sensor(es)?",
    "estaciones",
    "confirmando",
    "sonar",
    "calidad_red",
    "multicelda",
    "célula",
    "celula",
    "aviso",
    "fuerte",
    "advertencia",
    "Inventario",
    "Escuchando",
    "Cortado",
    "CALIBRANDO",
    "Seleccionando",
    "útil",
    "prueba",
    "paralela",
    "principal",
    "modifica",
    "sistema",
    "estado",
    "mensaje",
    "nivel",
]

ALLOW_LEGACY_KEYS = [
    '"sensores"',
    '"reservas"',
    '"sensores_activos"',
    '"sensores_calibrados"',
    '"sensores_totales"',
    '"estaciones_confirmando"',
    '"estaciones_confirmando_lista"',
    '"sonar"',
    '"calidad_red"',
    '"aviso_util"',
    '"mensaje"',
    '"nivel"',
    '"estado"',
    '"advertencia"',
    '"multicelda_parcial"',
    '"multicelda_fuerte"',
    '"remota_sin_local"',
    '"observacion_sin_sonido"',
]

ALLOW_PUBLIC_SPANISH = [
    "Red experimental. No reemplaza fuentes oficiales ni protocolos de emergencia.",
    "red multicelda parcial",
    "red multicelda alta",
    "normal multicelda",
    "señal compartida",
    "movimiento_posible",
]

regex = re.compile("|".join(PATTERNS), re.IGNORECASE)

def classify(line):
    if any(token in line for token in ALLOW_LEGACY_KEYS):
        return "legacy_compatibility"
    if any(token in line for token in ALLOW_PUBLIC_SPANISH):
        return "public_or_narrative"
    return "must_review"

rows = []

for filename in FILES:
    path = Path(filename)
    if not path.exists():
        continue
    for i, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
        if regex.search(line):
            rows.append((classify(line), filename, i, line.strip()))

out = []
out.append("# Cuyum v1.2 - Spanish audit in active core\n\n")
out.append("This report classifies Spanish remnants in active files.\n\n")

for category in ["must_review", "legacy_compatibility", "public_or_narrative"]:
    group = [r for r in rows if r[0] == category]
    out.append(f"## {category}\n\n")
    out.append(f"Count: {len(group)}\n\n")
    out.append("| file | line | text |\n")
    out.append("|---|---:|---|\n")
    for _, filename, line_no, text in group:
        safe = text.replace("|", "\\|")
        out.append(f"| `{filename}` | {line_no} | `{safe}` |\n")
    out.append("\n")

Path("REPORTE_IDIOMA_ACTIVO_V1_2.md").write_text("".join(out), encoding="utf-8")
print("Written: REPORTE_IDIOMA_ACTIVO_V1_2.md")
print("must_review:", sum(1 for r in rows if r[0] == "must_review"))
print("legacy_compatibility:", sum(1 for r in rows if r[0] == "legacy_compatibility"))
print("public_or_narrative:", sum(1 for r in rows if r[0] == "public_or_narrative"))
