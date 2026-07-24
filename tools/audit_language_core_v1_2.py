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

TERMS = [
    "estado",
    "archivo",
    "inventario",
    "candidatos",
    "modo",
    "sistema",
    "sensores",
    "estaciones",
    "confirmando",
    "sonar",
    "calidad_red",
    "multicelda",
    "celula",
    "célula",
    "aviso",
    "fuerte",
    "advertencia",
    "nivel",
    "mensaje",
    "activo",
    "activos",
    "calibrado",
    "calibrados",
    "caido",
    "caído",
    "sospechoso",
    "deshabilitado",
    "latencia",
    "energia",
    "útil",
    "prueba",
    "paralela",
    "principal",
    "principales",
    "reserva",
    "reservas",
    "dirección",
    "mínimo",
    "señal",
    "señales",
    "recuperado",
]

LEGACY_CONTRACT_HINTS = [
    "estado_grupo",
    "inventario_candidatos",
    "estado.json",
    "inventario.json",
    "sensores.json",
    '"estado"',
    '"nivel"',
    '"mensaje"',
    '"sonar"',
    '"calidad_red"',
    '"sensores',
    '"estaciones',
    '"aviso',
    '"advertencia"',
    '"modo"',
    '"sistema"',
    '"archivo',
    "cell_00_estado",
    "cell_00_sensores",
    "auto_cell_01_estado",
    "auto_cell_01_sensores",
    "auto_cell_01_aviso",
]

PUBLIC_ALLOWED_FILES = {
    "public_live.py",
    "event_journal.py",
}

regex = re.compile("|".join(re.escape(t) for t in TERMS), re.IGNORECASE)

def classify(filename, line):
    low = line.lower()

    if filename in PUBLIC_ALLOWED_FILES and any(word in low for word in [
        "public",
        "display",
        "summary",
        "description",
        "live",
    ]):
        return "public_allowed_review"

    if any(hint in line for hint in LEGACY_CONTRACT_HINTS):
        return "legacy_contract"

    if line.strip().startswith("#") or line.strip().startswith('"""') or line.strip().startswith("'''"):
        return "comment_or_docstring"

    return "must_fix"

rows = []

for filename in FILES:
    path = Path(filename)
    if not path.exists():
        continue

    for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
        if regex.search(line):
            rows.append((classify(filename, line), filename, line_no, line.strip()))

out = []
out.append("# Cuyum v1.2 language audit\n\n")

for category in ["must_fix", "comment_or_docstring", "legacy_contract", "public_allowed_review"]:
    group = [r for r in rows if r[0] == category]
    out.append(f"## {category}\n\n")
    out.append(f"Count: {len(group)}\n\n")
    out.append("| file | line | text |\n")
    out.append("|---|---:|---|\n")
    for _, filename, line_no, text in group:
        safe = text.replace("|", "\\|")
        out.append(f"| `{filename}` | {line_no} | `{safe}` |\n")
    out.append("\n")

Path("LANGUAGE_AUDIT_CORE_V1_2.md").write_text("".join(out), encoding="utf-8")

print("Written: LANGUAGE_AUDIT_CORE_V1_2.md")
for category in ["must_fix", "comment_or_docstring", "legacy_contract", "public_allowed_review"]:
    print(f"{category}:", sum(1 for r in rows if r[0] == category))
