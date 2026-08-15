import json, math
d=json.load(open(r'D:\方程验证\benchmark\stage4_full_ckpt_nl312.json'))
rows=d['rows'][:16]
oks=[r['ok'] for r in rows]

def X(n): return 60 + (620-60)*(n-1)/49.0   # n=1..50
def Y(p): return 340 - p*3.0                 # 0%->340, 100%->40

pts=[]
for n in range(1,17):
    p=sum(oks[:n])/n
    se=math.sqrt(p*(1-p)/n)
    hw=1.96*se
    pts.append((n,p,hw))

center=pts[-1][1]
band=[]
for n in range(16,51):
    p=center
    se=math.sqrt(p*(1-p)/n)
    hw=1.96*se
    band.append((n,p,hw))

W,H=680,380
svg=[]
svg.append(f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="system-ui,Arial">')
svg.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="#0f1420"/>')
for p in [0,25,50,75,100]:
    y=Y(p)
    svg.append(f'<line x1="60" y1="{y:.1f}" x2="620" y2="{y:.1f}" stroke="#2a3346" stroke-width="1"/>')
    svg.append(f'<text x="50" y="{y+4:.1f}" fill="#8b97ad" font-size="11" text-anchor="end">{p}%</text>')
ys=Y(0.74)
svg.append(f'<line x1="60" y1="{ys:.1f}" x2="620" y2="{ys:.1f}" stroke="#f59e0b" stroke-width="1.5" stroke-dasharray="6 4"/>')
svg.append(f'<text x="624" y="{ys+4:.1f}" fill="#f59e0b" font-size="11">solo 74%</text>')
up_l=[(X(n), Y(min(1.0,p+hw))) for n,p,hw in pts]
lo_l=[(X(n), Y(max(0.0,p-hw))) for n,p,hw in pts]
poly_up=' '.join(f'{x:.1f},{y:.1f}' for x,y in up_l)
poly_lo=' '.join(f'{x:.1f},{y:.1f}' for x,y in reversed(lo_l))
svg.append(f'<polygon points="{poly_up} {poly_lo}" fill="#1e3a5f" fill-opacity="0.55" stroke="#3b82f6" stroke-width="1" stroke-dasharray="3 3"/>')
up_r=[(X(n), Y(min(1.0,p+hw))) for n,p,hw in band]
lo_r=[(X(n), Y(max(0.0,p-hw))) for n,p,hw in band]
poly_up2=' '.join(f'{x:.1f},{y:.1f}' for x,y in up_r)
poly_lo2=' '.join(f'{x:.1f},{y:.1f}' for x,y in reversed(lo_r))
svg.append(f'<polygon points="{poly_up2} {poly_lo2}" fill="#1e3a5f" fill-opacity="0.55" stroke="#3b82f6" stroke-width="1" stroke-dasharray="3 3"/>')
line_pts=' '.join(f'{X(n):.1f},{Y(p):.1f}' for n,p,hw in pts)
svg.append(f'<polyline points="{line_pts}" fill="none" stroke="#ef4444" stroke-width="2.5"/>')
for n,p,hw in pts:
    svg.append(f'<circle cx="{X(n):.1f}" cy="{Y(p):.1f}" r="3" fill="#ef4444"/>')
xn=X(16)
svg.append(f'<line x1="{xn:.1f}" y1="40" x2="{xn:.1f}" y2="340" stroke="#64748b" stroke-width="1" stroke-dasharray="2 3"/>')
svg.append(f'<text x="{xn+4:.1f}" y="56" fill="#94a3b8" font-size="11">现在 n=16</text>')
svg.append(f'<text x="60" y="24" fill="#e2e8f0" font-size="15" font-weight="bold">full@12 运行准确率 + 95% 置信带（为什么数字在跳）</text>')
svg.append(f'<text x="60" y="366" fill="#94a3b8" font-size="11">红色锯齿=每题后的运行均值 · 蓝带=真实值所在的 95% 置信区间 · 带越宽=样本越小=跳得越狠</text>')
svg.append(f'<text x="60" y="352" fill="#f87171" font-size="11" font-weight="bold">n=16 时真实值在 [32%, 81%] 之间 — 当前 56% 在带里随便跳都正常，不是结果在变</text>')
svg.append('</svg>')

open(r'D:\方程验证\reports\full12_noise_band.html','w',encoding='utf-8').write('<!doctype html><meta charset=utf-8>'+''.join(svg))
print('saved')
