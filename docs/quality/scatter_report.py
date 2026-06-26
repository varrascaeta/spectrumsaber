import os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from radon.complexity import cc_visit
from radon.metrics import mi_visit
from radon.raw import analyze
from scipy.stats import pearsonr


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
            # First subdirectory under source_dir is the module
            rel = path.relative_to(source_dir)
            module = rel.parts[0] if len(rel.parts) > 1 else source_dir
            data.append(
                {
                    "name": str(path.name),
                    "module": module,
                    "cc": avg_cc,
                    "loc": loc,
                    "mi": mi,
                }
            )

locs = np.array([d["loc"] for d in data])
ccs = np.array([d["cc"] for d in data])
mis = np.array([d["mi"] for d in data])

x_line = np.linspace(locs.min(), locs.max(), 200)

r_cc, p_cc = pearsonr(locs, ccs)
r_mi, p_mi = pearsonr(locs, mis)


# ==============================
# LOGS: CC/LLOC and MI/LLOC
# ==============================

from collections import defaultdict

module_buckets = defaultdict(list)
for d in data:
    module_buckets[d["module"]].append(d)

print("\n--- CC/LLOC por módulo ---")
for mod in sorted(module_buckets):
    files = module_buckets[mod]
    ratios = [f["cc"] / f["loc"] for f in files]
    print(f"  {mod}: {sum(ratios) / len(ratios):.4f}")

global_cc_lloc = sum(d["cc"] / d["loc"] for d in data) / len(data)
print(f"  [global]: {global_cc_lloc:.4f}")

print("\n--- MI/LLOC por módulo ---")
for mod in sorted(module_buckets):
    files = module_buckets[mod]
    ratios = [f["mi"] / f["loc"] for f in files]
    print(f"  {mod}: {sum(ratios) / len(ratios):.4f}")

global_mi_lloc = sum(d["mi"] / d["loc"] for d in data) / len(data)
print(f"  [global]: {global_mi_lloc:.4f}\n")

print("--- Pearson r ---")
print(f"  CC vs LLOC: r={r_cc:.4f}, p={p_cc:.4e}")
print(f"  MI vs LLOC: r={r_mi:.4f}, p={p_mi:.4e}\n")


# ==============================
# PLOT 1: CC vs LLOC
# ==============================

fig, ax = plt.subplots(figsize=(10, 7))
ax.scatter(locs, ccs, alpha=0.6, s=80, color="steelblue", zorder=3)

z = np.polyfit(locs, ccs, 1)
p = np.poly1d(z)
ax.plot(
    x_line,
    p(x_line),
    "r--",
    linewidth=1.5,
    label=f"Tendencia lineal (y = {z[0]:.4f}x + {z[1]:.2f})\nr = {r_cc:.4f}, R² = {r_cc**2:.4f}, p = {p_cc:.2e}",
)

ax.set_xlabel("Líneas lógicas de código (LLOC)", fontsize=14)
ax.set_ylabel("Complejidad ciclomática (CC)", fontsize=14)
ax.set_title("CC vs. LLOC por módulo", fontsize=16)
ax.legend(fontsize=14)
ax.grid(True, linestyle="--", alpha=0.4)
ax.set_ylim(0, 10)
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
ax.plot(
    x_line,
    p2(x_line),
    "r--",
    linewidth=1.5,
    label=f"Tendencia lineal (y = {z2[0]:.4f}x + {z2[1]:.2f})\nr = {r_mi:.4f}, R² = {r_mi**2:.4f}, p = {p_mi:.2e}",
)

ax.set_xlabel("Líneas lógicas de código (LLOC)", fontsize=14)
ax.set_ylabel("Maintainability Index (MI)", fontsize=14)
ax.set_title("MI vs. LLOC por módulo", fontsize=16)
ax.legend(fontsize=14)
ax.grid(True, linestyle="--", alpha=0.4)
plt.tight_layout()
plt.savefig(MI_SCATTER_OUTPUT, dpi=300)
plt.close()

print(f"Gráfico guardado en {MI_SCATTER_OUTPUT}")
