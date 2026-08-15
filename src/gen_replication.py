#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 Stage2 严格复现对比报告(内联 SVG, 离线可用)."""
import json, math
from pathlib import Path

OUT = Path(r"C:/Users/11409/WorkBuddy/2026-07-28-21-49-24/gestalt_live")
ORIG = OUT / "stage2_live_original_backup.json"
REPS = [OUT / f"stage2_rep{i}_live.json" for i in (1, 2, 3)]
REP_NAMES = ["Rep1(greedy,n40)", "Rep2(temp0.5,n40)", "Rep3(temp0.5,n40)"]
OUT_HTML = Path(r"D:/方程验证/reports/replication_2026-08-03.html")

SERIES_COLORS = {"orig": "#2563eb", "rep1": "#16a34a", "rep2": "#ea580c", "rep3": "#9333ea"}


def load(path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def series_from(d, key):
    """从 live json 取 Ẇ->collective 的有序列表."""
    if not d:
        return None
    ca = d.get("collective_acc", {}) or {}
    conn = d.get("conn_levels") or []
    pts = []
    for cw in conn:
        k = f"cw{cw:.2f}"
        if k in ca and ca[k] is not None:
            pts.append((cw, ca[k]))
    if not pts:
        return None
    return {
        "points": pts,
        "best_single": d.get("best_single"),
        "committee0": d.get("committee0"),
        "status": d.get("status"),
        "n": d.get("n_questions"),
    }


def line_chart(title, series, w=720, h=420, ref_lines=None, y_min=0.4, y_max=1.0):
    """series: list of (label, color, [(x,y),...])"""
    ml, mr, mt, mb = 60, 20, 40, 50
    pw, ph = w - ml - mr, h - mt - mb
    xs = sorted({p[0] for s in series for p in s[2]})
    if not xs:
        xs = [0.0, 1.0]
    xmin, xmax = min(xs), max(xs)
    if xmax == xmin:
        xmax = xmin + 1
    def X(x):
        return ml + (x - xmin) / (xmax - xmin) * pw
    def Y(y):
        return mt + (1 - (y - y_min) / (y_max - y_min)) * ph

    svg = [f'<svg viewBox="0 0 {w} {h}" width="{w}" height="{h}" xmlns="http://www.w3.org/2000/svg">']
    svg.append(f'<rect x="0" y="0" width="{w}" height="{h}" fill="#ffffff"/>')
    svg.append(f'<text x="{w/2}" y="22" text-anchor="middle" font-size="15" font-weight="bold" fill="#111">{title}</text>')
    # y grid
    for gy in [0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
        if gy < y_min or gy > y_max:
            continue
        yy = Y(gy)
        svg.append(f'<line x1="{ml}" y1="{yy:.1f}" x2="{ml+pw}" y2="{yy:.1f}" stroke="#eee"/>')
        svg.append(f'<text x="{ml-6}" y="{yy+4:.1f}" text-anchor="end" font-size="10" fill="#888">{int(gy*100)}%</text>')
    # x ticks
    for gx in xs:
        xx = X(gx)
        svg.append(f'<text x="{xx:.1f}" y="{mt+ph+18}" text-anchor="middle" font-size="10" fill="#888">Ẇ={gx:.2f}</text>')
    # ref lines (e.g. best_single / committee0)
    if ref_lines:
        for rl in ref_lines:
            ry = Y(rl["y"])
            svg.append(f'<line x1="{ml}" y1="{ry:.1f}" x2="{ml+pw}" y2="{ry:.1f}" stroke="{rl["color"]}" stroke-dasharray="6 4" stroke-width="1.5"/>')
            svg.append(f'<text x="{ml+pw-4}" y="{ry-4:.1f}" text-anchor="end" font-size="10" fill="{rl["color"]}">{rl["label"]}</text>')
    # series
    for label, color, pts in series:
        if not pts:
            continue
        dpath = " ".join(f"L{x:.1f},{Y(y):.1f}" if i else f"M{x:.1f},{Y(y):.1f}" for i, (x, y) in enumerate(pts))
        svg.append(f'<path d="{dpath}" fill="none" stroke="{color}" stroke-width="2.5"/>')
        for x, y in pts:
            svg.append(f'<circle cx="{x:.1f}" cy="{Y(y):.1f}" r="4" fill="{color}"/>')
            svg.append(f'<text x="{x:.1f}" y="{Y(y)-8:.1f}" text-anchor="middle" font-size="10" fill="{color}">{y*100:.1f}</text>')
    # legend
    ly = mt + 8
    for label, color, pts in series:
        svg.append(f'<rect x="{ml+6}" y="{ly}" width="12" height="12" fill="{color}"/>')
        svg.append(f'<text x="{ml+22}" y="{ly+10}" font-size="11" fill="#222">{label}</text>')
        ly += 16
    svg.append('</svg>')
    return "".join(svg)


def bar_chart(title, bars, w=720, h=320):
    """bars: list of (label, value, color)"""
    ml, mr, mt, mb = 60, 20, 40, 60
    pw, ph = w - ml - mr, h - mt - mb
    vmin, vmax = 0.0, max(0.30, max(b[1] for b in bars) + 0.05)
    def Y(v):
        return mt + (1 - (v - vmin) / (vmax - vmin)) * ph
    svg = [f'<svg viewBox="0 0 {w} {h}" width="{w}" height="{h}" xmlns="http://www.w3.org/2000/svg">']
    svg.append(f'<rect width="{w}" height="{h}" fill="#fff"/>')
    svg.append(f'<text x="{w/2}" y="22" text-anchor="middle" font-size="15" font-weight="bold" fill="#111">{title}</text>')
    for gy in [0, 0.1, 0.2, 0.3]:
        if gy > vmax:
            continue
        yy = Y(gy)
        svg.append(f'<line x1="{ml}" y1="{yy:.1f}" x2="{ml+pw}" y2="{yy:.1f}" stroke="#eee"/>')
        svg.append(f'<text x="{ml-6}" y="{yy+4:.1f}" text-anchor="end" font-size="10" fill="#888">{gy*100:+.0f}</text>')
    n = len(bars)
    bw = pw / n * 0.6
    for i, (label, val, color) in enumerate(bars):
        cx = ml + (i + 0.5) * pw / n
        y0 = Y(0); y1 = Y(val)
        svg.append(f'<rect x="{cx-bw/2:.1f}" y="{min(y0,y1):.1f}" width="{bw:.1f}" height="{abs(y1-y0):.1f}" fill="{color}"/>')
        svg.append(f'<text x="{cx:.1f}" y="{y1-6 if val>=0 else y1+14:.1f}" text-anchor="middle" font-size="11" fill="{color}">{val*100:+.1f}</text>')
        svg.append(f'<text x="{cx:.1f}" y="{mt+ph+16}" text-anchor="middle" font-size="10" fill="#555">{label}</text>')
    svg.append('</svg>')
    return "".join(svg)


def main():
    orig = series_from(load(ORIG), "orig")
    reps = [(name, series_from(load(p), name)) for name, p in zip(REP_NAMES, REPS)]

    # Chart 1: collective vs Ẇ, all series + ref lines (orig best_single / committee0)
    series = []
    if orig:
        series.append(("Original(greedy,n30)", SERIES_COLORS["orig"], orig["points"]))
    for (name, s), col in zip(reps, [SERIES_COLORS["rep1"], SERIES_COLORS["rep2"], SERIES_COLORS["rep3"]]):
        if s:
            series.append((name, col, s["points"]))
    ref_lines = []
    if orig and orig["best_single"] is not None:
        ref_lines.append({"y": orig["best_single"], "color": "#dc2626", "label": f"最强单模型(原)={orig['best_single']*100:.0f}%"})
    if orig and orig["committee0"] is not None:
        ref_lines.append({"y": orig["committee0"], "color": "#0891b2", "label": f"投票基线(原)={orig['committee0']*100:.0f}%"})
    c1 = line_chart("集体合成准确率 vs 跨层连接强度 Ẇ", series, ref_lines=ref_lines)

    # Chart 2: beats_best margin per series (collective_max - best_single)
    bars = []
    if orig:
        cm = max(p[1] for p in orig["points"])
        bars.append(("Original", cm - orig["best_single"], SERIES_COLORS["orig"]))
    for (name, s), col in zip(reps, [SERIES_COLORS["rep1"], SERIES_COLORS["rep2"], SERIES_COLORS["rep3"]]):
        if s and s["best_single"] is not None:
            cm = max(p[1] for p in s["points"])
            bars.append((name.split("(")[0], cm - s["best_single"], col))
    c2 = bar_chart("beats_best 余量 (集体最优 − 最强单模型)", bars)

    # Chart 3: stochastic mean±std per Ẇ (rep2, rep3)
    stoch = [(name, s) for name, s in reps if s and "temp" in name and s["points"]]
    c3 = ""
    if len(stoch) >= 1:
        xs = sorted({p[0] for _, s in stoch for p in s["points"]})
        means, stds, ns = [], [], []
        for x in xs:
            ys = [next((p[1] for p in s["points"] if abs(p[0]-x) < 1e-6), None) for _, s in stoch]
            ys = [y for y in ys if y is not None]
            if ys:
                m = sum(ys)/len(ys)
                sd = (sum((y-m)**2 for y in ys)/len(ys))**0.5 if len(ys) > 1 else 0.0
                means.append(m); stds.append(sd); ns.append(len(ys))
        # draw mean line + min/max band
        ml, mr, mt, mb = 60, 20, 40, 50
        w, h = 720, 360
        pw, ph = w-ml-mr, h-mt-mb
        ymin, ymax = 0.4, 1.0
        def X(ix):
            return ml + (ix/(len(xs)-1) if len(xs) > 1 else 0.5) * pw
        def Y(v):
            return mt + (1-(v-ymin)/(ymax-ymin))*ph
        svg = [f'<svg viewBox="0 0 {w} {h}" width="{w}" height="{h}" xmlns="http://www.w3.org/2000/svg">']
        svg.append(f'<rect width="{w}" height="{h}" fill="#fff"/>')
        svg.append(f'<text x="{w/2}" y="22" text-anchor="middle" font-size="15" font-weight="bold" fill="#111">随机复现(Rep2/Rep3) 均值±跨度 vs Ẇ</text>')
        for gy in [0.4,0.5,0.6,0.7,0.8,0.9,1.0]:
            yy=Y(gy); svg.append(f'<line x1="{ml}" y1="{yy:.1f}" x2="{ml+pw}" y2="{yy:.1f}" stroke="#eee"/>')
            svg.append(f'<text x="{ml-6}" y="{yy+4:.1f}" text-anchor="end" font-size="10" fill="#888">{int(gy*100)}%</text>')
        # min/max band
        lo = [min(next(p[1] for p in s["points"] if abs(p[0]-x)<1e-6) for _,s in stoch) for x in xs]
        hi = [max(next(p[1] for p in s["points"] if abs(p[0]-x)<1e-6) for _,s in stoch) for x in xs]
        band = " ".join(f"L{X(i):.1f},{Y(hi[i]):.1f}" for i in range(len(xs))) + " " + " ".join(f"L{X(i):.1f},{Y(lo[i]):.1f}" for i in range(len(xs)-1,-1,-1))
        svg.append(f'<path d="M{band[1:]}" fill="#fdba74" opacity="0.35" stroke="none"/>' if False else f'<polygon points="{" ".join(f"{X(i):.1f},{Y(hi[i]):.1f}" for i in range(len(xs)))} {" ".join(f"{X(i):.1f},{Y(lo[i]):.1f}" for i in range(len(xs)-1,-1,-1))}" fill="#fdba74" opacity="0.4"/>')
        # mean line
        dpath = " ".join(f"L{X(i):.1f},{Y(means[i]):.1f}" if i else f"M{X(i):.1f},{Y(means[i]):.1f}" for i in range(len(xs)))
        svg.append(f'<path d="{dpath}" fill="none" stroke="#ea580c" stroke-width="2.5"/>')
        for i in range(len(xs)):
            svg.append(f'<circle cx="{X(i):.1f}" cy="{Y(means[i]):.1f}" r="4" fill="#ea580c"/>')
            svg.append(f'<text x="{X(i):.1f}" y="{Y(means[i])-8:.1f}" text-anchor="middle" font-size="10" fill="#ea580c">{means[i]*100:.1f}</text>')
            svg.append(f'<text x="{X(i):.1f}" y="{mt+ph+18}" text-anchor="middle" font-size="10" fill="#888">Ẇ={xs[i]:.2f}</text>')
        svg.append('</svg>')
        c3 = "".join(svg)

    # summary table
    rows = ""
    if orig:
        op = " / ".join(f"{p[1]*100:.1f}" for p in orig["points"])
        rows += f"<tr><td>Original (greedy, n30)</td><td>{op}</td><td>{orig['best_single']*100:.1f}%</td><td>{orig['committee0']*100:.1f}%</td><td>{'✅' if max(p[1] for p in orig['points'])>orig['best_single'] else '❌'}</td></tr>"
    for (name, s), col in zip(reps, ["rep1","rep2","rep3"]):
        if s:
            sp = " / ".join(f"{p[1]*100:.1f}" for p in s["points"])
            bs = s["best_single"]
            co = s["committee0"]
            rows += f"<tr><td>{name}</td><td>{sp}</td><td>{bs*100:.1f}%</td><td>{co*100:.1f}%</td><td>{'✅' if max(p[1] for p in s['points'])>bs else '❌'}</td></tr>"

    html = f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<title>格式塔方程 Stage2 严格复现对比</title>
<style>body{{font-family:-apple-system,Segoe UI,Roboto,'Microsoft YaHei',sans-serif;margin:24px;color:#1a1a1a;background:#fafafa}}
.card{{background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:16px;margin:14px 0;box-shadow:0 1px 3px rgba(0,0,0,.06)}}
h1{{font-size:20px}} h2{{font-size:15px;color:#374151;margin:6px 0 10px}}
table{{border-collapse:collapse;width:100%;font-size:13px}} th,td{{border:1px solid #e5e7eb;padding:6px 8px;text-align:center}}
th{{background:#f3f4f6}} .note{{font-size:12px;color:#6b7280;line-height:1.6}}</style></head>
<body><h1>格式塔方程 Stage2 —— 严格复现对比报告</h1>
<p class="note">生成时间 {time.strftime('%Y-%m-%d %H:%M')}。原始结果来自 n=30(首测); 复现用满 40 题 mcq_medium。
三档 Ẇ = 0.00 / 0.50 / 1.00 对应方程连接密度。判据: 集体最优 &gt; 最强单模型 ⇒ beats_best 成立(涌现协同)。</p>
<div class="card"><h2>图1 集体合成准确率 vs Ẇ(全序列)</h2>{c1}</div>
<div class="card"><h2>图2 beats_best 余量(集体最优 − 最强单模型)</h2>{c2}</div>
{'<div class="card"><h2>图3 随机复现均值±跨度</h2>'+c3+'</div>' if c3 else ''}
<div class="card"><h2>明细表</h2><table><tr><th>序列</th><th>集体(cw0.00/0.50/1.00)</th><th>最强单模型</th><th>投票基线</th><th>beats_best</th></tr>{rows}</table>
<p class="note">注: 原始 n=30 与复现 n=40 题集不同, 数值直接比较含题集位移; 复现内核是「满40题下集体仍 &gt; 最强单模型」这一结论是否稳定。</p></div>
</body></html>"""
    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"[done] {OUT_HTML}")


if __name__ == "__main__":
    main()
