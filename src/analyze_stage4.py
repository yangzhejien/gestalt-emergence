#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analyze_stage4.py — 拓扑密度扫描(G vs Ẇ)实时报告生成器
========================================================================
读 stage4 各档 checkpoint / final report / live, 计算
  G            = collective - committee0(L3投票)
  delta_vs_7b  = collective - solo 7b 基线
画出 G / delta_vs_7b 随密度(拓扑+节点数)的变化, 标记亚临界(Δ<0)与后临界(Δ>0)。
可重复运行: 每有新档落盘, 重跑即刷新。输出 reports/stage4_density_report.html (自包含, 无CDN)。
"""
import json
from pathlib import Path

BENCH = Path(r"D:\方程验证\benchmark")
RESULTS = Path(r"D:\方程验证\results")
LIVE = Path(r"C:\Users\11409\WorkBuddy\2026-07-28-21-49-24\gestalt_live\stage4_scan_live.json")
OUT = Path(r"D:\方程验证\reports\stage4_density_report.html")

def load_json(p):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None

# 密度顺序: 同 nl3 内 tree<mesh<full; nl3=20 整体更密(排后面)
ORDER = [("tree", 12), ("mesh", 12), ("full", 12),
         ("tree", 20), ("mesh", 20), ("full", 20)]

solo = load_json(BENCH / "stage4_solo_ckpt.json")
solo_val = solo.get("best_single") if solo else None
live = load_json(LIVE)

points = []  # (label, status, collective, comm0, G, delta, lateral_edges)
for topo, nl3 in ORDER:
    final = load_json(RESULTS / f"stage4_{topo}_final_nl3{nl3}.json")
    if final:
        coll = final["collective"]
        comm0 = final["committee0_L3vote"]
        points.append((f"{topo}@{nl3}", "done", coll, comm0,
                       final["G_collective_minus_comm0"],
                       final["delta_vs_7b"], final.get("lateral_edges")))
        continue
    # 进行中: 仅当前运行组的 live 含 partial
    if live and live.get("n_l3") == nl3:
        t = live.get("topos", {}).get(topo)
        if t and t.get("done", 0) > 0:
            coll = t["acc"]
            comm0 = t["comm0"]
            sv = live.get("solo_7b")
            points.append((f"{topo}@{nl3}", f"in-progress {t['done']}/50", coll, comm0,
                           round(coll - comm0, 4),
                           round(coll - sv, 4) if sv is not None else None,
                           None))

# ---------- 画图几何 ----------
W, H = 680, 380
PAD_L, PAD_R, PAD_T, PAD_B = 60, 30, 40, 60
plot_w = W - PAD_L - PAD_R
plot_h = H - PAD_T - PAD_B
n = len(ORDER)
x = lambda i: PAD_L + (plot_w * i / (n - 1)) if n > 1 else PAD_L + plot_w / 2

# y 范围: 覆盖所有 G 与 delta
ys = []
for p in points:
    if p[4] is not None: ys.append(p[4])
    if p[5] is not None: ys.append(p[5])
ys += [0.0]
ymin, ymax = min(ys), max(ys)
yr = max(ymax - ymin, 0.05)
ymin -= yr * 0.15
ymax += yr * 0.15
y = lambda v: PAD_T + plot_h * (1 - (v - ymin) / (ymax - ymin))

def fmt(v):
    return f"{v:+.3f}" if v is not None else "—"

# 点坐标(只在有数据的档画)
segs = []
for i, (topo, nl3) in enumerate(ORDER):
    hit = next((p for p in points if p[0] == f"{topo}@{nl3}"), None)
    if hit:
        segs.append((i, hit))

lines = []
# delta_vs_7b 主曲线(亚临界/后临界分界)
delta_pts = [(i, p[5]) for (i, p) in segs if p[5] is not None]
if len(delta_pts) >= 1:
    path = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in delta_pts)
    lines.append(("delta", path, "#2563eb"))
# G 次曲线
g_pts = [(i, p[4]) for (i, p) in segs if p[4] is not None]
if len(g_pts) >= 1:
    path = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in g_pts)
    lines.append(("G", path, "#d97706"))

# svg 构建
svg = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="system-ui,Segoe UI,Arial">']
# 网格 + y 轴刻度
for gy in [ymin, (ymin+ymax)/2, ymax]:
    yy = y(gy)
    svg.append(f'<line x1="{PAD_L}" y1="{yy:.1f}" x2="{W-PAD_R}" y2="{yy:.1f}" stroke="#eee"/>')
    svg.append(f'<text x="{PAD_L-8:.1f}" y="{yy+4:.1f}" text-anchor="end" font-size="11" fill="#666">{gy:+.2f}</text>')
# 零基线(delta=0 即 solo 等值线)
if ymin < 0 < ymax:
    zy = y(0.0)
    svg.append(f'<line x1="{PAD_L}" y1="{zy:.1f}" x2="{W-PAD_R}" y2="{zy:.1f}" stroke="#9ca3af" stroke-dasharray="5,4"/>')
    svg.append(f'<text x="{W-PAD_R}" y="{zy-5:.1f}" text-anchor="end" font-size="10" fill="#6b7280">solo 等值线 (Δ=0)</text>')
# 亚临界区标注(Δ<0 区域, 左侧低密度端)
svg.append(f'<rect x="{PAD_L}" y="{PAD_T}" width="{x(2)-PAD_L:.1f}" height="{plot_h}" fill="#f0f9ff" opacity="0.5"/>')
svg.append(f'<text x="{PAD_L+8:.1f}" y="{PAD_T+16:.1f}" font-size="10" fill="#0369a1">亚临界区 (Δ<0, 无涌现)</text>')
# x 轴标签
for i, (topo, nl3) in enumerate(ORDER):
    svg.append(f'<text x="{x(i):.1f}" y="{H-PAD_B+18:.1f}" text-anchor="middle" font-size="10" fill="#444">{topo}\n{nl3}</text>')
# x 轴标题
svg.append(f'<text x="{PAD_L+plot_w/2:.1f}" y="{H-8:.1f}" text-anchor="middle" font-size="11" fill="#333">拓扑密度 Ẇ 递增 → (tree &lt; mesh &lt; full, 12→20 节点)</text>')
# 曲线
for name, path, color in lines:
    svg.append(f'<polyline points="{path}" fill="none" stroke="{color}" stroke-width="2.5"/>')
# 数据点
for i, p in segs:
    cx, cy = x(i), y(p[5] if p[5] is not None else p[4])
    col = "#2563eb" if p[5] is not None else "#d97706"
    is_prog = "in-progress" in p[1]
    fill = "#fff" if is_prog else col
    svg.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="5" fill="{fill}" stroke="{col}" stroke-width="2"/>')
    svg.append(f'<text x="{cx:.1f}" y="{cy-10:.1f}" text-anchor="middle" font-size="9" fill="#222">{fmt(p[5] if p[5] is not None else p[4])}</text>')
svg.append('</svg>')

# 状态表
rows = ""
for p in points:
    rows += (f"<tr><td>{p[0]}</td><td>{p[1]}</td>"
             f"<td>{p[2]:.3f}</td><td>{p[3]:.3f}</td>"
             f"<td>{fmt(p[4])}</td><td>{fmt(p[5])}</td></tr>")
if not rows:
    rows = '<tr><td colspan="6" style="color:#999">尚无数据</td></tr>'

done_n = sum(1 for p in points if p[1] == "done")
prog_n = sum(1 for p in points if "in-progress" in p[1])

html = f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<title>Stage4 拓扑密度扫描 · G vs Ẇ</title>
<style>
body{{font-family:system-ui,'Segoe UI',Arial;margin:0;padding:24px;background:#fafafa;color:#1f2937}}
h1{{font-size:20px;margin:0 0 4px}} .sub{{color:#6b7280;font-size:13px;margin-bottom:16px}}
.banner{{background:#fff7ed;border:1px solid #fdba74;color:#9a3412;padding:10px 14px;border-radius:8px;font-size:13px;margin-bottom:16px}}
table{{border-collapse:collapse;width:100%;font-size:13px;background:#fff;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden}}
th,td{{padding:8px 10px;text-align:center;border-bottom:1px solid #f0f0f0}}
th{{background:#f3f4f6;color:#374151;font-weight:600}}
.card{{background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:16px;margin-bottom:16px}}
.legend{{font-size:12px;color:#555;margin-top:8px}}
.legend b{{color:#2563eb}} .legend i{{color:#d97706;font-style:normal}}
.note{{font-size:12px;color:#6b7280;margin-top:10px;line-height:1.5}}
</style></head><body>
<h1>Stage4 拓扑密度扫描 · 涌现 vs 密度 (G vs Ẇ)</h1>
<div class="sub">自检方程 M = Σsᵢ + Σ(αₘ−βₘ)Ẇ²ᵐ · 数据随扫描实时刷新 · solo 7B 基线 = {solo_val if solo_val is not None else '—'}</div>
<div class="banner">🟢 已完成 {done_n} 档 · 进行中 {prog_n} 档 · 待跑 {6-done_n-prog_n} 档。
n_l3=12 三档 G_solo<0（与亚临界假设一致, Wc 未定位）。上边界(full@20) + 随机拓扑基线 + C-Eval 待补, 方圈住 Wc。</div>
<div class="card">
{''.join(svg)}
<div class="legend">实线 <b>Δ(solo)</b> = 集体−7B基线(负=亚临界/无涌现, 正=后临界/涌现)；虚线 <i>G</i> = 集体−委员会0(结构增量)。空心点=进行中。</div>
</div>
<div class="card"><table>
<tr><th>档位</th><th>状态</th><th>集体</th><th>委员会0</th><th>G</th><th>Δ vs 7B</th></tr>
{rows}
</table>
<div class="note">说明: 横轴按拓扑密度递增排序(tree&lt;mesh&lt;full, 节点数 12→20)。当前仅 tree@12 为终态;
mesh@12 进行中(前3题小样本, 不计)。Wc 拐点需三档@12 与 @20 全出 + 随机拓扑基线对照方可见非单调峰。</div>
</div></body></html>"""

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(html, encoding="utf-8")
print(f"[report] 写入 {OUT} | 完成{done_n} 进行{prog_n} 待跑{6-done_n-prog_n}")
for p in points:
    print(f"  {p[0]:10s} {p[1]:16s} coll={p[2]:.3f} comm0={p[3]:.3f} G={fmt(p[4])} Δ={fmt(p[5])}")
