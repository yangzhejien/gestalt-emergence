# -*- coding: utf-8 -*-
"""把 stage2_live.json 烤成一个自包含、无 fetch 的静态 HTML 快照。
   这样用户通过文件预览即可查看, 不依赖 localhost 网络可达性。"""
import json
from pathlib import Path

LIVE = Path(r"C:/Users/11409/WorkBuddy/2026-07-28-21-49-24/gestalt_live/stage2_live.json")
OUT = Path(r"C:/Users/11409/WorkBuddy/2026-07-28-21-49-24/gestalt_live/stage2_snapshot.html")

def main():
    d = json.loads(LIVE.read_text(encoding="utf-8")) if LIVE.exists() else {}
    data_js = json.dumps(d, ensure_ascii=False)
    node_labels = ["L3-1(1.5b)", "L3-2(1.5b)", "L3-3(1.5b)", "L2副脑(3b)", "L1主脑(7b)"]
    html = TEMPLATE.replace("__DATA__", data_js).replace("__LABELS__", json.dumps(node_labels, ensure_ascii=False))
    OUT.write_text(html, encoding="utf-8")
    print(f"[render_static] wrote {OUT}  ({OUT.stat().st_size} bytes)")

TEMPLATE = r"""<!doctype html><html lang="zh"><head><meta charset="utf-8">
<title>格式塔方程验证 · Stage 2 · 静态快照</title>
<style>
 body{background:#0e1116;color:#e6edf3;font:14px/1.5 -apple-system,Segoe UI,Roboto,monospace;margin:0;padding:18px}
 h1{font-size:18px;margin:0 0 4px}
 .sub{color:#8b949e;font-size:12px;margin-bottom:14px}
 .pill{display:inline-block;background:#21262d;border:1px solid #30363d;border-radius:10px;padding:2px 9px;margin:2px;font-size:12px}
 .run{color:#7ee787}.done{color:#58a6ff}
 .card{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:14px;margin:12px 0}
 .row{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:6px 0}
 canvas{background:#0e1116;border:1px solid #30363d;border-radius:8px;display:block;margin-top:8px}
 pre{white-space:pre-wrap;background:#0e1116;border:1px solid #30363d;border-radius:8px;padding:10px;font-size:12px;color:#a5d6ff}
 .big{font-size:22px;font-weight:700}
 .warn{color:#f0883e}
</style></head><body>
<h1>格式塔方程验证 · Stage 2（协作合成，非投票）</h1>
<div class="sub">静态快照 · 每次汇报由 render_static.py 重新烤制 · 非实时轮询</div>
<div id="app">加载中…</div>
<script>
const D = __DATA__;
const NODE_LABELS = __LABELS__;
const PAL = ['#58a6ff','#7ee787','#f0883e','#bc8cff','#ff7b72','#56d4dd'];
function fmt(v){return v==null?'?':(typeof v==='number'? (Math.abs(v)<10? v.toFixed(3):v.toFixed(1)) : v);}
function barsCanvas(vals,labels,id,opt){
  opt=opt||{};
  const c=document.createElement('canvas');c.width=640;c.height=260;c.id=id;
  const x=c.getContext('2d');const max=Math.max(1,...vals.map(v=>v==null?0:v))*1.1;
  const bw=c.width/(vals.length+1);
  vals.forEach((v,i)=>{const h=(v/max)*(c.height-40);const bx=bw*(i+0.5);
    x.fillStyle=PAL[i%PAL.length];x.fillRect(bx-bw*0.32,c.height-24-h,bw*0.64,h);
    x.fillStyle='#e6edf3';x.font='12px monospace';x.textAlign='center';
    x.fillText(labels[i],bx,c.height-8);
    x.fillText((v*100).toFixed(0)+'%',bx,c.height-28-h);});
  x.strokeStyle='#30363d';x.beginPath();x.moveTo(0,c.height-24);x.lineTo(c.width,c.height-24);x.stroke();
  return c;
}
function curveCanvas(pts){
  const c=document.createElement('canvas');c.width=640;c.height=260;
  const x=c.getContext('2d');
  const maxW=Math.max(0.0001,...pts.map(p=>p.What));
  const X=v=>20+v/maxW*(c.width-40);
  const allY=pts.map(p=>p.G).concat([0]);const maxY=Math.max(0.3,...allY.map(Math.abs))*1.3;
  const Y=v=>c.height/2-(v/maxY)*(c.height/2-15);
  x.strokeStyle='#30363d';x.beginPath();x.moveTo(20,c.height/2);x.lineTo(c.width-10,c.height/2);x.stroke();
  x.strokeStyle='#21262d';x.beginPath();x.moveTo(20,10);x.lineTo(20,c.height-10);x.stroke();
  x.fillStyle='#8b949e';x.font='11px monospace';x.fillText('G',4,16);x.fillText('conn_w',c.width-50,c.height/2-6);
  pts.forEach(p=>{x.fillStyle=PAL[0];x.beginPath();x.arc(X(p.What),Y(p.G),5,0,7);x.fill();
    x.fillStyle='#8b949e';x.font='10px monospace';x.fillText('cw'+p.What,X(p.What)-12,Y(p.G)-8);});
  if(pts.length<2){x.fillStyle='#8b949e';x.fillText('需≥2点画曲线;当前'+pts.length+'点',28,30);}
  return c;
}
function build(){
  const app=document.getElementById('app');app.innerHTML='';
  const st=D.status||'idle';
  let h='';
  h+='<div class="row"><span class="pill '+(st==='done'?'done':st==='running'?'run':'')+'">'+st+'</span>';
  h+='<span class="pill">'+ (D.phase||'?') +'</span>';
  h+='<span class="pill">updated '+ (D.updated_at||'?') +'</span></div>';
  h+='<div class="row"><span class="pill">进度</span> <b>'+ (D.progress||'—') +'</b></div>';
  const m=D.models||{};
  h+='<div class="row"><span class="pill">L3</span>'+ (m.l3||'?') +
     ' <span class="pill">聚合/L2</span>'+ (m.agg||'?') +
     ' <span class="pill">L1</span>'+ (m.l1||'?') +
     ' <span class="pill">验证</span>'+ (m.verifier||'?') +'</div>';
  h+='<div class="row"><span class="pill">n='+(D.n_questions||'?')+'</span><span class="pill">conn_w='+JSON.stringify(D.conn_levels||[])+'</span></div>';
  app.innerHTML=h;

  // 基线卡片
  const card1=document.createElement('div');card1.className='card';
  let c1='<b>单模型基线（判据 beats_best 参照）</b><div class="row">';
  const na=D.node_acc||[];
  na.forEach((v,i)=>{c1+='<span class="pill">'+ (NODE_LABELS[i]||('node'+i)) +'</span> <b>'+(v*100).toFixed(0)+'%</b> ';});
  c1+='</div>';
  c1+='<div class="row"><span class="pill">最强单模型 best_single</span> <span class="big">'+ fmt(D.best_single) +'</span>';
  c1+=' <span class="pill">L3直接投票 committee0</span> <b>'+ fmt(D.committee0) +'</b></div>';
  c1+='<canvas id="b1"></canvas>';
  card1.innerHTML=c1;app.appendChild(card1);
  const b1=document.getElementById('b1');
  const bx=b1.getContext('2d');const _v=na.concat([D.best_single||0]);const _l=NODE_LABELS.slice(0,na.length).concat(['最强单模型']);
  const bc=barsCanvas(_v,_l,'b1');b1.replaceWith(bc);

  // 协作合成卡片
  const card2=document.createElement('div');card2.className='card';
  // 优先 points; 兜底 collective_acc(每档实时写), 让本轮回合也能显示已出档位
  let pts=[];
  if(D.points&&D.points.length){ pts=D.points.filter(p=>p.What!==undefined); }
  else if(D.collective_acc){
    pts=Object.keys(D.collective_acc).map(k=>{const w=parseFloat((''+k).replace('cw',''));return {What:w,collective:D.collective_acc[k],committee0:D.committee0,G:(D.collective_acc[k]-(D.committee0||0))};});
  }
  let c2='<b>协作合成集体准确率（按 conn_w 分档）</b>';
  if(pts.length===0){c2+='<div class="warn">还没有档位结果（pipeline 进行中）…</div>';}
  else{
    c2+='<div class="row">';
    pts.forEach(p=>{c2+='<span class="pill">conn_w='+p.What+'</span> 集体 <b>'+(p.collective*100).toFixed(0)+'%</b> · G='+ (p.G>=0?'+':'')+(p.G*100).toFixed(0)+'% &nbsp; ';});
    c2+='</div>';
    c2+='<div class="row"><span class="pill">beats_best(集体>最强单模型)?</span> <b>'+(D.judgement||'—')+'</b></div>';
    c2+='<canvas id="cv"></canvas>';
  }
  card2.innerHTML=c2;app.appendChild(card2);
  if(pts.length>0){const cv=document.getElementById('cv');const cc=curveCanvas(pts);cv.replaceWith(cc);}

  // 判定/备注
  const card3=document.createElement('div');card3.className='card';
  let c3='<b>当前判读</b><pre>';
  if(!D.judgement){c3+='（尚在采集, 无最终判定）\n';}
  else{c3+=D.judgement+'\n';}
  c3+='\n说明: 本快照为静态烤制, 数字以最新一次烤制时刻为准。\n';
  c3+='best_single 与 committee0 已出 → 单模型底线已测得。\n';
  c3+='各 conn_w 档位的 collective 出来后即可首次对比「集体 vs 最强单模型」。';
  c3+='</pre>';card3.innerHTML=c3;app.appendChild(card3);
}
build();
</script></body></html>"""

if __name__ == "__main__":
    main()
