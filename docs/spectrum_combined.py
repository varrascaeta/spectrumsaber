import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.gridspec import GridSpec
from scipy.interpolate import make_interp_spline, PchipInterpolator

# ── Digitized curves (wavelength µm, reflectance %) ─────────────────────────
# Agua: monotone decreasing in visible, ~0 after 0.75µm.
# Two small bumps at ~0.44 and ~0.55 are real features (scattering/absorption).
wl_agua = np.array([0.40, 0.43, 0.46, 0.50, 0.54, 0.57, 0.60, 0.63, 0.66,
                    0.69, 0.72, 0.75, 0.80, 0.82, 0.84, 0.86, 0.88, 0.9, 1.00, 1.1, 1.15, 1.2, 2.80])
r_agua  = np.array([18.0, 18.5, 19.0, 18.5,  18,  16,  14,  13,  12,
                     10,  8,  7.5,  6, 5, 4, 3.5, 2.5, 2, 1.5, 1, 0.6,  0.1, 0.0])

wl_suelo = np.array([0.40, 0.50, 0.60, 0.70, 0.80, 1.00, 1.20, 1.40, 1.60, 1.80, 2.00, 2.20, 2.40, 2.60, 2.80])
r_suelo  = np.array([16.0, 18.0, 20.0, 21.5, 23.0, 25.0, 26.5, 27.5, 29.0, 27.0, 28.5, 31.0, 33.5, 32.0, 28.5])

wl_sana = np.array([0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.68, 0.70, 0.73, 0.75, 0.80, 0.90,
                    1.00, 1.10, 1.20, 1.30, 1.35, 1.40, 1.45, 1.50, 1.60, 1.65, 1.70,
                    1.80, 1.88, 1.95, 2.00, 2.10, 2.15, 2.20, 2.30, 2.40, 2.55, 2.65, 2.80])
r_sana  = np.array([ 8.0,  7.0,  9.5, 13.0,  9.0,  7.0,  5.0,  8.0, 28.0, 45.0, 55.0, 56.0,
                    54.0, 53.5, 52.0, 22.0, 18.0, 22.0, 25.0, 35.0, 40.0, 38.0, 34.0,
                    20.0, 17.0, 19.0, 22.0, 20.0, 17.0, 14.5, 10.0,  7.0,  4.0,  2.0,  0.5])

wl_enferma = np.array([0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.68, 0.70, 0.73, 0.75, 0.80, 0.90,
                       1.00, 1.10, 1.20, 1.30, 1.35, 1.40, 1.45, 1.50, 1.60, 1.65, 1.70,
                       1.80, 1.88, 1.95, 2.00, 2.10, 2.15, 2.20, 2.30, 2.40, 2.55, 2.65, 2.80])
r_enferma  = np.array([10.0,  9.0, 11.0, 13.0, 10.5,  8.5,  7.0, 10.0, 18.0, 25.0, 33.0, 33.5,
                       32.0, 31.0, 30.0, 16.0, 13.5, 16.0, 19.5, 23.5, 29.0, 27.5, 24.5,
                       14.5, 12.0, 13.5, 15.5, 14.0, 12.0, 10.0,  7.0,  5.0,  3.0,  1.2,  0.2])


def smooth(wl, r, n=500, pchip=False):
    wl_fine = np.linspace(wl[0], wl[-1], n)
    if pchip:
        interp = PchipInterpolator(wl, r)
    else:
        interp = make_interp_spline(wl, r, k=3)
    return wl_fine, np.clip(interp(wl_fine), 0, 100)


# ── Figure layout ────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(12, 7))
gs = GridSpec(2, 1, height_ratios=[1, 6], hspace=0.04)

ax_bar   = fig.add_subplot(gs[0])
ax_refl  = fig.add_subplot(gs[1])

# ── Spectrum bar ─────────────────────────────────────────────────────────────
vis_nodes = [
    (0.00, '#8B00FF'), (0.12, '#4400FF'), (0.22, '#0055FF'),
    (0.33, '#00CC00'), (0.48, '#AAFF00'), (0.56, '#FFFF00'),
    (0.73, '#FF7700'), (1.00, '#FF0000'),
]
cmap_vis = LinearSegmentedColormap.from_list('vis', vis_nodes)

gradient = np.linspace(0, 1, 400).reshape(1, -1)
ax_bar.imshow(gradient, extent=[0.40, 0.70, 0, 1], aspect='auto', cmap=cmap_vis, zorder=2)
ax_bar.barh(0.5, 0.70, left=0.70, height=1.0, color='#FF6666', alpha=0.80, zorder=2)
ax_bar.barh(0.5, 0.50, left=1.40, height=1.0, color='#CC3333', alpha=0.80, zorder=2)
ax_bar.barh(0.5, 0.90, left=1.90, height=1.0, color='#882222', alpha=0.80, zorder=2)

abs_bands = [(1.35, 1.45, 'H₂O'), (1.80, 1.95, 'H₂O'), (2.60, 2.80, 'CO₂')]
for s, e, lbl in abs_bands:
    ax_bar.barh(0.5, e - s, left=s, height=1.0, color='#888888', alpha=0.6, zorder=3)
    ax_bar.text((s + e) / 2, 0.5, lbl, ha='center', va='center',
                fontsize=7, color='white', fontweight='bold', zorder=4)

region_labels = [
    (0.550, 'VIS'),
    (1.050, 'NIR'),
    (1.650, 'SWIR-1'),
    (2.350, 'SWIR-2'),
]
for x, txt in region_labels:
    ax_bar.text(x, 0.5, txt, ha='center', va='center',
                fontsize=8.5, fontweight='bold', color='white',
                zorder=5, alpha=0.92)

ax_bar.set_xlim(0.4, 2.8)
ax_bar.set_ylim(0, 1)
ax_bar.set_yticks([])
ax_bar.set_xticks([])
ax_bar.spines[:].set_visible(False)

# ── Reflectance plot ─────────────────────────────────────────────────────────
# Absorption band shading
for s, e, _ in abs_bands:
    ax_refl.axvspan(s, e, color='#CCCCCC', alpha=0.4, zorder=1)

wl_f, r_f = smooth(wl_agua,    r_agua,    pchip=True)
ax_refl.plot(wl_f, r_f, 'k-.', lw=1.5, label='Agua')

wl_f, r_f = smooth(wl_suelo,   r_suelo,   pchip=True)
ax_refl.plot(wl_f, r_f, 'k--', lw=1.5, label='Suelo')

wl_f, r_f = smooth(wl_enferma, r_enferma, pchip=True)
ax_refl.plot(wl_f, r_f, 'k-',  lw=1.2, label='Vegetación enferma')

wl_f, r_f = smooth(wl_sana,    r_sana,    pchip=True)
ax_refl.plot(wl_f, r_f, 'k-',  lw=2.5, label='Vegetación sana')

# Annotations
ax_refl.annotate('Vegetación sana',   xy=(0.85, 55), xytext=(1.0, 68),
                 arrowprops=dict(arrowstyle='->', color='black', lw=0.8), fontsize=9)
ax_refl.annotate('Vegetación enferma', xy=(1.0, 32), xytext=(1.15, 44),
                 arrowprops=dict(arrowstyle='->', color='black', lw=0.8), fontsize=9)
ax_refl.annotate('Suelo',              xy=(2.2, 31), xytext=(2.3, 42),
                 arrowprops=dict(arrowstyle='->', color='black', lw=0.8), fontsize=9)
ax_refl.annotate('Agua',               xy=(0.6,  5), xytext=(0.75, 12),
                 arrowprops=dict(arrowstyle='->', color='black', lw=0.8), fontsize=9)

ax_refl.set_xlim(0.4, 2.8)
ax_refl.set_ylim(0, 85)
ax_refl.set_xlabel('Longitud de onda (µm)', fontsize=11)
ax_refl.set_ylabel('Reflectancia (%)', fontsize=11)
ax_refl.xaxis.set_major_locator(plt.MultipleLocator(0.4))
ax_refl.xaxis.set_minor_locator(plt.MultipleLocator(0.2))
ax_refl.set_xticks([0.4, 0.8, 1.2, 1.6, 2.0, 2.4, 2.8])
ax_refl.set_xticklabels(['0,4', '0,8', '1,2', '1,6', '2,0', '2,4', '2,8'])
ax_refl.tick_params(axis='both', labelsize=9)
ax_refl.spines['top'].set_visible(False)
ax_refl.spines['right'].set_visible(False)

# µm label at right
ax_refl.text(2.82, -6, 'µm', fontsize=9, va='top', ha='left', clip_on=False)

plt.savefig('docs/spectrum_combined.png', dpi=180, bbox_inches='tight',
            facecolor='white')
print("Guardado: docs/spectrum_combined.png")
