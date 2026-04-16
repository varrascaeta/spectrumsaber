import os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from radon.complexity import cc_visit
from radon.metrics import mi_visit
from radon.raw import analyze


# ==============================
# CONFIG
# ==============================

SOURCE_DIRS = ["src"]
EXCLUDE_FOLDERS = {"__pycache__", "migrations", "__init__.py"}

CC_SCATTER_OUTPUT = "docs/quality/cc_loc_scatter.png"
MI_SCATTER_OUTPUT = "docs/quality/mi_loc_scatter.png"


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


def short_name(path_str: str) -> str:
    parts = Path(path_str).parts
    if parts[0] in ("src", "spectrumsaber"):
        parts = parts[1:]
    return "/".join(parts)


def analyze_file(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()

    blocks = cc_visit(source)
    avg_cc = sum(b.complexity for b in blocks) / len(blocks) if blocks else 0

    raw = analyze(source)
    loc = raw.lloc

    mi_score = mi_visit(source, multi=True)

    return avg_cc, loc, mi_score


# ==============================
# DATA COLLECTION
# ==============================

data = []
for source_dir in SOURCE_DIRS:
    for root, _, files in os.walk(source_dir):
        for file in files:
            path = Path(root) / file
            if not is_relevant_file(path):
                continue
            avg_cc, loc, mi = analyze_file(path)
            if loc == 0:
                continue
            data.append({
                "name": str(path.name),
                "cc": avg_cc,
                "loc": loc,
                "mi": mi,
            })

locs = np.array([d["loc"] for d in data])
ccs = np.array([d["cc"] for d in data])
mis = np.array([d["mi"] for d in data])

x_line = np.linspace(locs.min(), locs.max(), 200)


# ==============================
# PLOT 1: CC vs LLOC
# ==============================

fig, ax = plt.subplots(figsize=(10, 7))
ax.scatter(locs, ccs, alpha=0.6, s=80, color="steelblue", zorder=3)

z = np.polyfit(locs, ccs, 1)
p = np.poly1d(z)
ax.plot(x_line, p(x_line), "r--", linewidth=1.5,
        label=f"Tendencia lineal (y = {z[0]:.4f}x + {z[1]:.2f})")

ax.set_xlabel("Líneas lógicas de código (LLOC)", fontsize=14)
ax.set_ylabel("Complejidad ciclomática (CC)", fontsize=14)
ax.set_title("CC vs. LLOC por módulo", fontsize=16)
ax.legend(fontsize=14)
ax.grid(True, linestyle="--", alpha=0.4)
plt.tight_layout()
plt.savefig(CC_SCATTER_OUTPUT, dpi=300)
plt.close()

print(f"Gráfico guardado en {CC_SCATTER_OUTPUT}")


# ==============================
# PLOT 2: MI vs LLOC
# ==============================

fig, ax = plt.subplots(figsize=(10, 7))
ax.scatter(locs, mis, alpha=0.6, s=80, color="darkorange", zorder=3)

z2 = np.polyfit(locs, mis, 1)
p2 = np.poly1d(z2)
ax.plot(x_line, p2(x_line), "r--", linewidth=1.5,
        label=f"Tendencia lineal (y = {z2[0]:.4f}x + {z2[1]:.2f})")

ax.set_xlabel("Líneas lógicas de código (LLOC)", fontsize=14)
ax.set_ylabel("Maintainability Index (MI)", fontsize=14)
ax.set_title("MI vs. LLOC por módulo", fontsize=16)
ax.legend(fontsize=14)
ax.grid(True, linestyle="--", alpha=0.4)
plt.tight_layout()
plt.savefig(MI_SCATTER_OUTPUT, dpi=300)
plt.close()

print(f"Gráfico guardado en {MI_SCATTER_OUTPUT}")
