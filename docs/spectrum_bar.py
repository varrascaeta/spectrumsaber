import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import LinearSegmentedColormap

fig, ax = plt.subplots(figsize=(14, 3))

# --- Visible region: 0.4–0.7 µm with rainbow gradient ---
vis_colors = [
    (0.40, '#8B00FF'),  # violet
    (0.45, '#4400FF'),  # blue-violet
    (0.49, '#0055FF'),  # blue
    (0.52, '#00CC00'),  # green
    (0.57, '#AAFF00'),  # yellow-green
    (0.59, '#FFFF00'),  # yellow
    (0.62, '#FF7700'),  # orange
    (0.70, '#FF0000'),  # red
]
xs = [c[0] for c in vis_colors]
cs = [c[1] for c in vis_colors]
cmap_vis = LinearSegmentedColormap.from_list('vis', list(zip(
    [(x - 0.40) / (0.70 - 0.40) for x in xs], cs
)))

gradient = np.linspace(0, 1, 300).reshape(1, -1)
ax.imshow(gradient, extent=[0.40, 0.70, 0, 1], aspect='auto',
          cmap=cmap_vis, zorder=2)

# --- NIR: 0.7–1.4 µm ---
ax.barh(0.5, 0.70, left=0.70, height=1.0, color='#FF6666', alpha=0.75, zorder=2)

# --- SWIR-1: 1.4–1.9 µm ---
ax.barh(0.5, 0.50, left=1.40, height=1.0, color='#CC3333', alpha=0.75, zorder=2)

# --- SWIR-2: 1.9–2.8 µm ---
ax.barh(0.5, 0.90, left=1.90, height=1.0, color='#882222', alpha=0.75, zorder=2)

# --- Atmospheric absorption bands (grey overlay) ---
absorption_bands = [
    (1.35, 1.45, 'H₂O'),
    (1.80, 1.95, 'H₂O'),
    (2.60, 2.80, 'CO₂/H₂O'),
]
for start, end, label in absorption_bands:
    ax.barh(0.5, end - start, left=start, height=1.0,
            color='grey', alpha=0.55, zorder=3)
    ax.text((start + end) / 2, 0.5, label,
            ha='center', va='center', fontsize=7, color='white',
            fontweight='bold', zorder=4)

# --- Region labels ---
labels = [
    (0.55,  'Visible\n(0.4–0.7 µm)'),
    (1.05,  'NIR\n(0.7–1.4 µm)'),
    (1.65,  'SWIR-1\n(1.4–1.9 µm)'),
    (2.35,  'SWIR-2\n(1.9–2.8 µm)'),
]
for x, txt in labels:
    ax.text(x, 1.18, txt, ha='center', va='bottom', fontsize=9,
            fontweight='bold', color='#222222')

# --- Axis formatting ---
ax.set_xlim(0.4, 2.8)
ax.set_ylim(0, 1.5)
ax.set_xlabel('Longitud de onda (µm)', fontsize=11)
ax.set_yticks([])
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:.1f}'))
ax.xaxis.set_major_locator(plt.MultipleLocator(0.2))
ax.tick_params(axis='x', labelsize=9)
ax.spines[['top', 'left', 'right']].set_visible(False)

plt.title('Espectro electromagnético — rango óptico e infrarrojo', fontsize=12, pad=18)
plt.tight_layout()
plt.savefig('docs/spectrum_bar.png', dpi=150, bbox_inches='tight')
plt.show()
print("Guardado: docs/spectrum_bar.png")
