import os
from pathlib import Path

import matplotlib.pyplot as plt
from radon.complexity import cc_visit
from radon.metrics import mi_visit
from radon.raw import analyze


# ==============================
# CONFIG
# ==============================

SOURCE_DIR = "src"  # Cambiar si querés incluir también spectrumsaber
EXCLUDE_FOLDERS = {
    "tests",
    "__pycache__",
    "migrations",
    "__init__.py",
    "apps.py",
}
OUTPUT_IMAGE = "docs/quality/mi_density_report.png"


# ==============================
# HELPERS
# ==============================


def is_relevant_file(path: Path) -> bool:
    """Return True if file should be analyzed."""
    if path.suffix != ".py":
        return False

    for part in path.parts:
        if part in EXCLUDE_FOLDERS:
            return False

    return True


def analyze_file(path: Path):
    """Return (avg_cc, mi_score) for file."""
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()

    # Cyclomatic complexity
    blocks = cc_visit(source)
    if blocks:
        avg_cc = sum(b.complexity for b in blocks) / len(blocks)
    else:
        avg_cc = 0

    # Maintainability Index
    mi_score = mi_visit(source, multi=True)
    analysis = analyze(source)

    return avg_cc, mi_score, analysis


# ==============================
# MAIN ANALYSIS
# ==============================

results = {}
for source_dir in [SOURCE_DIR, "spectrumsaber"]:
    for root, _, files in os.walk(source_dir):
        for file in files:
            path = Path(root) / file

            if not is_relevant_file(path):
                continue

            avg_cc, mi_score, analysis = analyze_file(path)

            # Mostrar solo archivos relevantes
            if avg_cc > 0 or mi_score > 0:
                results[str(path)] = {
                    "cc": avg_cc,
                    "mi": mi_score,
                    "loc": analysis.loc,
                    "lloc": analysis.lloc,
                    "sloc": analysis.sloc,
                }

# Ordenar por MI descendente
results = dict(sorted(results.items(), key=lambda x: x[1]["mi"], reverse=True))


# ==============================
# PRINT TABLE
# ==============================

print("\n==== Métricas por módulo ====\n")
average_mi = (
    sum(data["mi"] for data in results.values()) / len(results)
    if results
    else 0
)
print(f"MI Promedio: {average_mi:.2f}\n")
for module, data in results.items():
    print(
        f"{module:<60} "
        f"CC: {data['cc']:.2f} | "
        f"MI: {data['mi']:.2f} | "
        f"LOC: {data['loc']} | "
        f"LLOC: {data['lloc']} | "
        f"SLOC: {data['sloc']}"
    )

# ==============================
# PLOT
# ==============================

modules = list(results.keys())
mi_scores = [data["mi"] for data in results.values()]

plt.figure(figsize=(10, 8))
plt.barh(modules, mi_scores)
plt.xlabel("Maintainability Index (MI)")
plt.title("Índice de Mantenibilidad por Módulo")
plt.gca().invert_yaxis()  # mayor arriba
plt.tight_layout()
plt.xticks(range(0, 101, 10))
plt.savefig(OUTPUT_IMAGE, dpi=300)
plt.show()

print(f"\nGráfico guardado en {OUTPUT_IMAGE}")
