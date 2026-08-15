#!/usr/bin/env python3
# probe_node_alt.py — 用备选模型(如 abliterate:3b)在硬题池上 solo 测难度, 判断能否替换坍塌的 L2 节点
# 用法: python probe_node_alt.py --model huihui_ai/qwen2.5-abliterate:3b --out benchmark/node_ablate3b.json
# 特性: 断点续跑 + 逐题重试(抗 Ollama 抖动) + 写 live(看板)
import sys, os, json, argparse, time, ast, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify_stage2 as V
from verify_stage4_topology import run_solo
ROOT = V.ROOT
POOL = ROOT / "benchmark" / "mcq_hard_pool.jsonl"
LIVE = V.OUT / "node_alt_live.json"

def write_live(d):
    try:
        tmp = LIVE.with_suffix(".tmp")
        tmp.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, LIVE)
    except Exception as e:
        sys.stderr.write(f"[live fail] {e}\n"); sys.stderr.flush()

def load_ckpt(p):
    if p.exists():
        try: return json.loads(p.read_text(encoding="utf-8")).get("r", [])
        except Exception: return []
    return []

def save_ckpt(p, r):
    try:
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps({"r": r}, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, p)
    except Exception as e:
        sys.stderr.write(f"[ckpt fail] {e}\n"); sys.stderr.flush()

def safe_run(qn, cfg, model, tries=3):
    last = None
    for t in range(tries):
        try:
            return run_solo(qn, cfg, model)
        except Exception as e:
            last = e; sys.stderr.write(f"  [retry {t+1}] {model}: {e}\n"); sys.stderr.flush(); time.sleep(1.5+t)
    return None

def normalize(q):
    opts = q.get("options")
    if isinstance(opts, str):
        try: opts = ast.literal_eval(opts)
        except Exception: opts = {}
    if not isinstance(opts, dict): opts = {}
    return {"question": q.get("q", q.get("question","")), "A": opts.get("A"), "B": opts.get("B"),
            "C": opts.get("C"), "D": opts.get("D"), "answer": q.get("answer", q.get("A"))}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--no-resume", action="store_true")
    args = ap.parse_args()
    qs = [json.loads(l) for l in open(POOL, encoding="utf-8") if l.strip()]
    ckpt = ROOT / "benchmark" / ("node_alt_" + args.model.replace("/","_").replace(":","_") + "_ckpt.json")
    if args.no_resume and ckpt.exists(): ckpt.unlink()
    r = load_ckpt(ckpt)
    print(f"[node_alt] model={args.model} pool={len(qs)} 续={len(r)}", flush=True)
    cfg = dict(V.DEFAULT_CFG)
    V.warmup_models(cfg)
    for i in range(len(r), len(qs)):
        qn = normalize(qs[i])
        c = safe_run(qn, cfg, args.model)
        r.append(c == qn["answer"] if c is not None else False)
        if (i+1) % 20 == 0:
            print(f"  {i+1}/{len(qs)} acc={sum(r)/(i+1):.3f}", flush=True)
        write_live({"status":"running","phase":"node-alt","progress":f"{args.model} {i+1}/{len(qs)} acc={sum(r)/(i+1):.3f}",
                    "n":len(qs),"done":i+1,"acc":sum(r)/(i+1),"updated_at":time.strftime("%H:%M:%S")})
        save_ckpt(ckpt, r)
    acc = sum(r)/len(r)
    res = {"model": args.model, "pool": len(qs), "acc": round(acc,4), "above_chance": acc>0.25, "usable_as_L2": acc>0.40}
    json.dump(res, open(ROOT/args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if ckpt.exists(): ckpt.unlink()
    print(f"[node_alt] DONE {args.model} acc={acc:.4f} above_chance={acc>0.25} usable={acc>0.40}", flush=True)
    write_live({"status":"done","phase":"node-alt-final","progress":f"{args.model} acc={acc:.3f} usable={acc>0.40}",
                "n":len(qs),"done":len(qs),"acc":acc,"updated_at":time.strftime("%H:%M:%S")})

if __name__ == "__main__":
    try: main()
    except Exception:
        traceback.print_exc()
        write_live({"status":"error","phase":"crashed","progress":"node_alt 崩溃, 见日志/ckpt(可续跑)","updated_at":time.strftime("%H:%M:%S")})
        raise
