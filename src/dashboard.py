#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
格式塔方程验证 - 网页实时监测看板 (仅标准库)
================================================
启动:  python scripts/dashboard.py
浏览:  http://localhost:8000
看板每 1.5s 轮询 data/live.json, 实时绘制:
  - 节点准确率 / 委员会基线 柱状图
  - G ~ W_hat 散点 + 偶次幂拟合曲线
  - 拟合系数 alpha1/alpha2, R2, 判定
"""
import json, http.server, socketserver, threading, sys
from pathlib import Path

# 实时数据文件放在沙箱允许的工作区目录(后台任务沙箱拒绝写 D:\)。
# 可通过 --live <path> 指定监控不同实验的 live 文件, --port <n> 指定端口, 从而多实例并存。
LIVE = Path(r"C:/Users/11409/WorkBuddy/2026-07-28-21-49-24/gestalt_live/live.json")
PORT = 8000


def parse_args():
    """解析 --live <path> / --port <n>, 覆盖默认监控文件与端口。"""
    global LIVE, PORT
    a = sys.argv[1:]
    i = 0
    while i < len(a):
        if a[i] in ("--live", "-l") and i + 1 < len(a):
            LIVE = Path(a[i + 1]); i += 2
        elif a[i] in ("--port", "-p") and i + 1 < len(a):
            try:
                PORT = int(a[i + 1])
            except ValueError:
                pass
            i += 2
        else:
            i += 1

HTML = r"""<!doctype html><html lang="zh"><head><meta charset="utf-8">
<title>格式塔方程验证 · 实时监测</title>
<style>
  body{background:#0e1116;color:#e6edf3;font:14px/1.5 -apple-system,Segoe UI,Roboto,monospace;margin:0;padding:16px}
  h1{font-size:18px;margin:0 0 4px}
  .sub{color:#8b949e;font-size:12px;margin-bottom:14px}
  .grid{display:flex;gap:16px;flex-wrap:wrap}
  .card{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:12px 14px;min-width:300px;flex:1}
  .card h2{font-size:13px;color:#58a6ff;margin:0 0 8px;letter-spacing:.5px}
  canvas{width:100%;height:240px;display:block;background:#0d1117;border-radius:6px}
  .stat{display:flex;gap:18px;flex-wrap:wrap;margin-top:8px}
  .stat b{color:#7ee787}
  .pill{display:inline-block;padding:2px 8px;border-radius:999px;font-size:12px;background:#21262d;color:#8b949e}
  .pill.run{background:#1f6feb33;color:#58a6ff}
  .pill.done{background:#23863633;color:#7ee787}
  pre{white-space:pre-wrap;color:#e6edf3;font-size:12px;margin:6px 0 0}
</style></head>
<body>
<h1>格式塔方程验证 · 实时监测</h1>
<div class="sub">Gestalt Equation Head Verification — live dashboard &nbsp;|&nbsp; 刷新间隔 1.5s</div>
<div class="grid">
  <div class="card"><h2>状态 / STATUS</h2>
    <div id="status"><span class="pill">idle</span></div>
    <div id="progress" class="sub"></div>
    <div class="stat" id="stat"></div>
  </div>
  <div class="card"><h2>节点准确率 / 基线</h2>
    <canvas id="bars" width="560" height="240"></canvas>
  </div>
  <div class="card"><h2>G ~ W_hat 曲线 (偶次幂拟合)</h2>
    <canvas id="curve" width="560" height="240"></canvas>
  </div>
  <div class="card" style="flex-basis:100%"><h2>拟合 / 判定</h2>
    <pre id="fit"></pre>
  </div>
</div>
<script>
const PAL=['#58a6ff','#7ee787','#ffa657','#ff7b72','#d2a8ff'];
function fmt(x){return (x===null||x===undefined||Number.isNaN(x))?'—':(+x).toFixed(4);}
async function poll(){
  let d={status:'idle'};
  try{const r=await fetch('/data',{cache:'no-store'});d=await r.json();}catch(e){}
  // 兼容: 若进程未显式写 current_w(如 stage3 20节点实验), 从 collective_acc 末键反推 W 档
  if((d.current_w===null||d.current_w===undefined)&&d.collective_acc){
    const ks=Object.keys(d.collective_acc);
    if(ks.length){const m=(''+ks[ks.length-1]).replace('cw','');const w=parseFloat(m);if(!Number.isNaN(w))d.current_w=w;}
  }
  // status pill
  const st=d.status||'idle';
    document.getElementById('status').innerHTML=
    '<span class="pill '+(st==='done'?'done':st==='running'?'run':'')+'">'+st+
    (d.phase?' · '+d.phase:'')+(d.current_w!==null&&d.current_w!==undefined?' · w='+d.current_w:'')+'</span>';
    document.getElementById('progress').textContent = d.progress || '';
  // stat
  let s='';
  s+='<div><span class="pill">模型</span> <b>'+(d.node_model||'?')+'</b></div>';
  s+='<div><span class="pill">k='+(d.k||'?')+'</span> <span class="pill">n='+(d.n_questions||'?')+'</span></div>';
  s+='<div><span class="pill">updated</span> <b>'+(d.updated_at||'?')+'</b></div>';
  // 实时集体准确率高亮(真正随题推进在涨的数) + 当前 G
  const cw = d.current_w;
  if(cw!==null&&cw!==undefined&&d.collective_acc){
    const ck='cw'+Number(cw).toFixed(2);
    const cv=d.collective_acc[ck];
    if(cv!==null&&cv!==undefined){
      const g=(cv-(d.committee0||0));
      s+='<div style="margin-top:8px"><span class="pill run">实时集体@W'+cw+'</span> <b style="font-size:18px;color:#7ee787">'+ (cv*100).toFixed(1) +'%</b>';
      s+=' &nbsp; <span class="pill">G='+ (g>=0?'+':'') + (g*100).toFixed(1) +'%</span>';
      s+=' &nbsp; <span class="pill">基线A_net0='+ ((d.committee0||0)*100).toFixed(0) +'%</span></div>';
    }
  }
  document.getElementById('stat').innerHTML=s;
  drawBars(d);
  drawCurve(d);
  // fit text
  const np=(d.points||[]).length;
  const pts4=(d.points||[]).filter(p=>p.What!==undefined);
  const cf = np>=4 ? fit24obj(pts4) : null;
  let f='';
  if(d.fit){const ft=d.fit;
    const a1 = cf?cf.a1:ft.alpha1, a2 = cf?cf.a2:ft.alpha2, r2 = cf?cf.r2:ft.r2;
    f+='alpha1 = '+fmt(a1)+'   alpha2 = '+fmt(a2)+'\n';
    f+='R2(even) = '+fmt(r2)+'   R2(linear) = '+fmt(ft.r2_lin)+'\n';
    if(ft.alpha1_ci)f+='alpha1 95%CI = ['+fmt(ft.alpha1_ci[0])+', '+fmt(ft.alpha1_ci[1])+']\n';
    if(ft.alpha2_ci)f+='alpha2 95%CI = ['+fmt(ft.alpha2_ci[0])+', '+fmt(ft.alpha2_ci[1])+']\n';
    if(cf)f+='(拟合由看板按实测点实时计算, 非进程缓存)\n';
  } else f='(拟合进行中, 需 >=2 个数据点)\n';
  if(np<5)f+='\n⚠ 数据点='+np+' < 5,系数/R² 仅反映趋势,不可作为结论\n';
  f+='\n判定: '+(d.judgement||'—');
  document.getElementById('fit').textContent=f;
}
function drawBars(d){
  const c=document.getElementById('bars'),x=c.getContext('2d');x.clearRect(0,0,c.width,c.height);
  const vals=[];const labels=[];const cols=[];
  const naRaw = d.node_acc || [];
  const naIsArr = Array.isArray(naRaw);
  const naVals = naIsArr ? naRaw : Object.values(naRaw);
  const naLabels = naIsArr ? naRaw.map((_,i)=>'node'+(i+1)) : Object.keys(naRaw);
  naVals.forEach((v,i)=>{vals.push(v==null?0:v);labels.push(naLabels[i]||('node'+(i+1)));cols.push(PAL[i%PAL.length]);});
  if(d.A_net0!==null&&d.A_net0!==undefined){vals.push(d.A_net0);labels.push('A_net(0)基线');cols.push('#8b949e');}
  // 实时集体准确率(当前 W 档) — 绿色高亮, 随题推进动态变化; 这是真正在涨的数
  const curW = d.current_w;
  if(curW!==null&&curW!==undefined&&d.collective_acc){
    const ck='cw'+Number(curW).toFixed(2);
    const cv=d.collective_acc[ck];
    if(cv!==null&&cv!==undefined){vals.push(cv);labels.push('集体@W'+curW);cols.push('#7ee787');}
  }
  if(vals.length===0){
    x.fillStyle='#8b949e';x.font='14px monospace';x.textAlign='center';
    x.fillText('Phase A 基线测评中 · 节点柱将逐项填充', c.width/2, c.height/2-10);
    x.fillText('（流水线集体阶段才出现绿色「集体@W」柱）', c.width/2, c.height/2+14);
    x.strokeStyle='#30363d';x.beginPath();x.moveTo(0,c.height-20);x.lineTo(c.width,c.height-20);x.stroke();
    return;
  }
  const max=Math.max(1,...vals)*1.1;const bw=c.width/(vals.length+1);
  vals.forEach((v,i)=>{
    const h=(v/max)*(c.height-30);const bx=bw*(i+0.5);
    x.fillStyle=cols[i]||PAL[i%PAL.length];x.fillRect(bx-bw*0.3,c.height-20-h,bw*0.6,h);
    x.fillStyle='#e6edf3';x.font='12px monospace';x.textAlign='center';
    x.fillText(labels[i],bx,c.height-6);
    x.fillText((v*100).toFixed(0)+'%',bx,c.height-24-h);
  });
  x.strokeStyle='#30363d';x.beginPath();x.moveTo(0,c.height-20);x.lineTo(c.width,c.height-20);x.stroke();
}
function fit24obj(pts){
  // 客户端实时最小二乘拟合 G ~ a1*W^2 + a2*W^4 (不依赖进程缓存的 fit 字段, 永不过时)
  let s22=0,s44=0,s24=0,s2g=0,s4g=0,sg=0,sg2=0;
  for(const p of pts){
    const w2=p.What*p.What, w4=w2*w2, w6=w4*w2, w8=w4*w4;
    s22+=w4; s44+=w8; s24+=w6; s2g+=w2*p.G; s4g+=w4*p.G; sg+=p.G; sg2+=p.G*p.G;
  }
  const D=s22*s44-s24*s24; if(Math.abs(D)<1e-12)return null;
  const a1=(s2g*s44-s24*s4g)/D, a2=(s22*s4g-s24*s2g)/D, mean=sg/pts.length;
  let ssr=0;
  for(const p of pts){const w2=p.What*p.What, w4=w2*w2; const y=a1*w2+a2*w4; ssr+=(p.G-y)*(p.G-y);}
  const sst=sg2-pts.length*mean*mean;
  const r2= sst>1e-12 ? 1-ssr/sst : 1;
  return {a1:a1,a2:a2,r2:r2};
}
function drawCurve(d){
  const c=document.getElementById('curve'),x=c.getContext('2d');x.clearRect(0,0,c.width,c.height);
  // 优先用 points(脚本末尾统一写); 兜底用 collective_acc(每档结束实时写), 让本轮回合也能逐档显示
  let pts=[];
  if(d.points&&d.points.length){ pts=d.points.filter(p=>p.What!==undefined); }
  else if(d.collective_acc){
    pts=Object.keys(d.collective_acc).map(k=>{const w=parseFloat((''+k).replace('cw',''));return {What:w,w:w,collective:d.collective_acc[k],committee0:d.committee0,G:(d.collective_acc[k]-(d.committee0||0))};});
  }
  const maxWhat=Math.max(0.0001,...pts.map(p=>p.What));
  const X=v=>20+v/Math.max(1,maxWhat)*(c.width-40);
  const allY=pts.map(p=>p.G).concat([0]);const maxY=Math.max(0.5,...allY.map(Math.abs))*1.2;
  const Y=v=>c.height/2 - (v/maxY)*(c.height/2-15);
  // axes
  x.strokeStyle='#30363d';x.beginPath();x.moveTo(20,c.height/2);x.lineTo(c.width-10,c.height/2);x.stroke();
  x.strokeStyle='#21262d';x.beginPath();x.moveTo(20,10);x.lineTo(20,c.height-10);x.stroke();
  x.fillStyle='#8b949e';x.font='11px monospace';x.fillText('G',4,16);x.fillText('W_hat',c.width-44,c.height/2-6);
  // fit curve — computed client-side from measured points (never stale), dashed, within range, >=4 pts
  if(pts.length>=3){
    const f=fit24obj(pts);
    if(f){x.strokeStyle='#7ee787';x.setLineDash([5,4]);x.beginPath();
      for(let i=0;i<=60;i++){const v=i/60*maxWhat;const y=f.a1*v*v+f.a2*v*v*v*v;
        const px=X(v),py=Y(y);i===0?x.moveTo(px,py):x.lineTo(px,py);}
      x.stroke();x.setLineDash([]);
    }
  } else if(pts.length>0){
    x.fillStyle='#8b949e';x.font='11px monospace';x.fillText('拟合需 ≥3 点(防过拟合假象);当前 '+pts.length+' 点',28,30);
  } else {
    x.fillStyle='#8b949e';x.font='12px monospace';x.fillText('等待协作合成数据… (solo 基线阶段, 节点条已在上方更新)',28,30);
  }
  // points
  pts.forEach((p,i)=>{x.fillStyle=PAL[i%PAL.length];x.beginPath();x.arc(X(p.What),Y(p.G),5,0,7);x.fill();
    x.fillStyle='#8b949e';x.font='10px monospace';x.fillText('w'+p.w,X(p.What)-12,Y(p.G)-8);});
}
poll();setInterval(poll,1500);
</script></body></html>"""


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            body = HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/data":
            payload = b'{"status":"idle"}'
            if LIVE.exists():
                try:
                    payload = LIVE.read_bytes()
                except Exception:
                    pass
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(payload)
        else:
            self.send_response(404); self.end_headers()

    def log_message(self, *a):
        pass


def main():
    httpd = socketserver.ThreadingTCPServer(("0.0.0.0", PORT), Handler)
    print(f"[dashboard] serving on http://localhost:{PORT}  (Ctrl+C to stop)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.shutdown()


if __name__ == "__main__":
    parse_args()
    if LIVE.name != "live.json":
        # 非默认文件时, 在看板标题标注实验名, 便于多实例区分
        HTML = HTML.replace("格式塔方程验证 · 实时监测",
                            "格式塔方程验证 · " + LIVE.stem + " · 实时监测")
    main()
