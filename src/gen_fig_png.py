# -*- coding: utf-8 -*-
"""Regenerate the 4 preregistration figures as PNG via matplotlib (no cairo needed),
matching the content of the original SVGs."""
import os, numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch

REP = r"D:\方程验证\reports"
os.makedirs(REP, exist_ok=True)

# ---- theory net gain curve: net(W) = -0.18 + a*W^4 - b*W^6, Wc=1.0, peak ~ +0.25 ----
a, b = 1.29, 0.86
def net(W):
    return -0.18 + a*W**4 - b*W**6
Wc = 1.0

# ===================== FIG 1: theory prediction =====================
fig, ax = plt.subplots(figsize=(7, 4.2))
W = np.linspace(0.05, 1.5, 400)
ax.plot(W, net(W), color='#1f77b4', lw=2.4, label=r'Net emergence $G(\hat W)$')
ax.axvline(Wc, color='#d62728', ls='--', lw=1.8)
ax.text(Wc+0.02, 0.12, r'$W_c^*=\sqrt{\alpha_1/\alpha_2}$', color='#d62728', fontsize=11)
ax.axhline(0, color='#888', lw=0.8)
ax.axvspan(0.05, Wc, color='#ffd6d6', alpha=0.25, label=r'sub-critical ($\hat W<W_c$)')
ax.axvspan(Wc, 1.5, color='#d6ecff', alpha=0.25, label=r'super-critical ($\hat W>W_c$)')
ax.set_xlabel(r'Normalized cross-layer connection density $\hat W$', fontsize=11)
ax.set_ylabel('Net emergence gain  G', fontsize=11)
ax.set_title('Figure 1. Theory: non-monotonic emergence vs connection density', fontsize=12, fontweight='bold')
ax.set_ylim(-0.9, 0.45)
ax.legend(fontsize=9, loc='lower right')
ax.grid(alpha=0.25)
fig.tight_layout()
fig.savefig(os.path.join(REP, 'fig1_theory.png'), dpi=150)
plt.close(fig)

# ===================== FIG 2: empirical status =====================
fig, ax = plt.subplots(figsize=(7, 4.2))
ax.plot(W, net(W), color='#1f77b4', lw=2.2, label=r'Theory curve $G(\hat W)$')
ax.axvline(Wc, color='#d62728', ls='--', lw=1.6)
ax.text(Wc+0.02, 0.13, r'$W_c^*$', color='#d62728', fontsize=11)
# empirical points
pts = [  # x, G, ci, label, color
    (0.35, -0.16, 0.13, 'tree@12 (n=50)', '#2ca02c'),
    (0.60, -0.22, 0.13, 'mesh@12 (n=50)', '#2ca02c'),
    (0.80, -0.10, 0.13, 'full@12 (n=50)', '#2ca02c'),
    (1.05, +0.17, 0.30, 'full@20 (n=6 exploratory)', '#d62728'),
]
for x, y, ci, lab, c in pts:
    ax.errorbar(x, y, yerr=ci, fmt='o', color=c, ms=9, capsize=5, lw=2, label=f'{lab}  G={y:+.2f}')
ax.axhline(0, color='#888', lw=0.8)
ax.set_xlabel(r'Normalized cross-layer connection density $\hat W$', fontsize=11)
ax.set_ylabel('Net emergence gain  G_solo', fontsize=11)
ax.set_title('Figure 2. Current empirical status (green=clean n=50; red=n=6 anchor)', fontsize=11.5, fontweight='bold')
ax.set_ylim(-0.9, 0.55)
ax.legend(fontsize=8.5, loc='lower right')
ax.grid(alpha=0.25)
fig.tight_layout()
fig.savefig(os.path.join(REP, 'fig2_empirical.png'), dpi=150)
plt.close(fig)

# ===================== FIG 3: structural emergence bars =====================
fig, ax = plt.subplots(figsize=(7, 4.2))
tops = ['tree@12', 'mesh@12', 'full@12']
coll = [0.58, 0.52, 0.64]
comm0 = [0.50, 0.50, 0.50]
solo = 0.74
x = np.arange(len(tops)); w = 0.35
ax.bar(x - w/2, coll, w, color='#1f77b4', label='collective')
ax.bar(x + w/2, comm0, w, color='#999999', label='committee-0 (L3 vote)')
ax.axhline(solo, color='#ff7f0e', ls='--', lw=2, label='solo-7B (0.74)')
for i, v in enumerate(coll):
    ax.text(i - w/2, v + 0.01, f'{v:.2f}', ha='center', fontsize=9)
    ax.text(i + w/2, comm0[i] + 0.01, f'{comm0[i]:.2f}', ha='center', fontsize=9)
ax.set_xticks(x); ax.set_xticklabels(tops)
ax.set_ylabel('Accuracy', fontsize=11)
ax.set_ylim(0, 0.85)
ax.set_title('Figure 3. Structural cross-layer emergence (H1 holds; H2 pending)', fontsize=11.5, fontweight='bold')
ax.legend(fontsize=9)
ax.grid(alpha=0.25, axis='y')
fig.tight_layout()
fig.savefig(os.path.join(REP, 'fig3_structural.png'), dpi=150)
plt.close(fig)

# ===================== FIG 4: topology schematic =====================
def draw_topo(ax, kind):
    ax.set_xlim(-0.2, 1.2); ax.set_ylim(-0.2, 1.2); ax.axis('off')
    # L1 top, L2 mid, L3 bottom cluster
    L1 = np.array([[0.5, 1.0]])
    L2 = np.array([[0.5, 0.6]]) if kind != 'mesh' else np.array([[0.3,0.6],[0.5,0.6],[0.7,0.6]])
    if kind == 'full':
        L3 = np.array([[0.15,0.2],[0.35,0.2],[0.5,0.2],[0.65,0.2],[0.85,0.2]])
    else:
        L3 = np.array([[0.2,0.2],[0.4,0.2],[0.6,0.2],[0.8,0.2]])
    # edges L3->L2
    for p3 in L3:
        for p2 in L2:
            ax.plot([p3[0],p2[0]],[p3[1],p2[1]], color='#bbb', lw=0.8, zorder=1)
    # edges L2->L1
    for p2 in L2:
        ax.plot([p2[0],L1[0,0]],[p2[1],L1[0,1]], color='#555', lw=1.2, zorder=1)
    if kind == 'mesh':
        for i in range(len(L2)):
            for j in range(i+1,len(L2)):
                ax.plot([L2[i,0],L2[j,0]],[L2[i,1],L2[j,1]], color='#2ca02c', lw=1.4, zorder=1)
    if kind == 'full':
        for i in range(len(L3)):
            for j in range(i+1,len(L3)):
                ax.plot([L3[i,0],L3[j,0]],[L3[i,1],L3[j,1]], color='#d62728', lw=1.2, zorder=1)
    # nodes
    ax.scatter(L1[:,0], L1[:,1], s=260, color='#ff7f0e', zorder=3, edgecolor='k')
    ax.scatter(L2[:,0], L2[:,1], s=220, color='#1f77b4', zorder=3, edgecolor='k')
    ax.scatter(L3[:,0], L3[:,1], s=120, color='#9467bd', zorder=3, edgecolor='k')
    ax.text(0.5, 1.12, 'L1 (7B)', ha='center', fontsize=9)
    ax.text(0.5, 0.70, 'L2 (3B)', ha='center', fontsize=9)
    ax.text(0.5, 0.05, 'L3 (1.5B x n)', ha='center', fontsize=9)
    if kind == 'tree':
        ax.set_title(r'tree' + '\n(low $\hat W$)', fontsize=10)
    elif kind == 'mesh':
        ax.set_title('mesh\n(+ L2 full-connect)', fontsize=10)
    else:
        ax.set_title('full\n(+ L3 intra-cluster)', fontsize=10)

fig, axes = plt.subplots(1, 3, figsize=(9, 3.6))
draw_topo(axes[0], 'tree'); draw_topo(axes[1], 'mesh'); draw_topo(axes[2], 'full')
fig.suptitle('Figure 4. Experimental design: cross-layer density sweep', fontsize=12, fontweight='bold')
fig.tight_layout()
fig.savefig(os.path.join(REP, 'fig4_topologies.png'), dpi=150)
plt.close(fig)
print("figures written to", REP)
for f in ['fig1_theory.png','fig2_empirical.png','fig3_structural.png','fig4_topologies.png']:
    print(" ", f, os.path.getsize(os.path.join(REP, f)), "bytes")
