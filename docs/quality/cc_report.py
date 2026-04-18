import os
from pathlib import Path

import matplotlib.pyplot as plt
from radon.complexity import cc_visit
from radon.raw import analyze


# ==============================
# CONFIG
# ==============================

SOURCE_DIR = "src"
EXCLUDE_FOLDERS = {
    "tests",
    "__pycache__",
    "migrations",
    "__init__.py",
    "apps.py",
}
OUTPUT_IMAGE = "docs/quality/cc_density_report.png"


# ==============================
# HELPERS
# ==============================


def is_relevant_file(path: Path) -> bool:
    if path.suffix != ".py":
        return False
    for part in path.parts:
        if part in EXCLUDE_FOLDERS:
            return False
    return True


def analyze_file(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()

    # Complejidad ciclomática
    blocks = cc_visit(source)
    avg_cc = sum(b.complexity for b in blocks) / len(blocks) if blocks else 0

    # Líneas reales de código
    raw = analyze(source)
    loc = raw.lloc

    return avg_cc, loc


# ==============================
# MAIN
# ==============================

results = {}
for source_dir in [SOURCE_DIR, "spectrumsaber"]:
    for root, _, files in os.walk(source_dir):
        for file in files:
            path = Path(root) / file

            if not is_relevant_file(path):
                continue

            avg_cc, loc = analyze_file(path)

            if loc == 0:
                continue

            cc_density = avg_cc / loc
            results[str(path)] = {
                "cc": avg_cc,
                "loc": loc,
                "density": cc_density,
            }

# Ordenar por densidad descendente
results = dict(
    sorted(results.items(), key=lambda x: x[1]["density"], reverse=True)
)

# ==============================
# PRINT
# ==============================

print("\n==== CC normalizada por LOC ====\n")
for module, data in results.items():
    print(
        f"{module:<60} "
        f"CC: {data['cc']:.2f} | "
        f"LOC: {data['loc']:4} | "
        f"CC/LOC: {data['density']:.5f}"
    )

# ==============================
# PLOT
# ==============================

modules = list(results.keys())
densities = [data["density"] for data in results.values()]

plt.figure(figsize=(10, 8))
plt.barh(modules, densities)
plt.xlabel("Complejidad Ciclotomática / LOC")
plt.title("Densidad de Complejidad por Módulo")
plt.gca().invert_yaxis()
plt.tight_layout()
plt.savefig(OUTPUT_IMAGE, dpi=300)
plt.show()

print(f"\nGráfico guardado en {OUTPUT_IMAGE}")
