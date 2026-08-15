#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
prep_pubbench.py — 公开标准集交叉验证准备 (C-Eval 中文多选)
========================================================================
目的: 用标准公开基准(C-Eval)替代自造题, 做密度扫描的**交叉验证**,
      封堵顶刊审稿对"自造题研究者自由度"的质疑。

两阶段(解耦, 避免与密度扫描抢 Ollama CPU):
  --download : 从 hf-mirror 拉 C-Eval val(52 学科 parquet), 转候选 pool jsonl
               (同 schema: question/A/B/C/D/answer/subject)。仅需网络, 不碰 Ollama。
  --probe    : 用 1.5B/3B/7B 逐题探针(run_solo, 与密度扫描同答案解析口径),
               算每模型 acc, 贪心过滤出 band_ok 子集 -> ceval_bandok_clean.jsonl + probe json。

控制变量: 模型 = verify_stage2.DEFAULT_CFG (原版 qwen2.5:1.5b/3b/7b), 与自造集扫描完全一致。
band_ok 口径(与 mcq_midhard 相同): 7b<1.0(留头顶空间) 且 3b>0.25 且 15b>0.25(每层有实值)。
"""
import sys, os, json, argparse, urllib.request, socket, random, time
sys.path.insert(0, r"D:\方程验证\scripts")
import verify_stage2 as V
import verify_stage4_topology as S4

HF = "https://hf-mirror.com/datasets/ceval/ceval-exam/resolve/main"
BENCH_DIR = r"D:\方程验证\benchmark"
socket.setdefaulttimeout(60)

def fetch_subjects():
    """动态获取 C-Eval 52 学科目录名"""
    url = "https://hf-mirror.com/api/datasets/ceval/ceval-exam/tree/main"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as r:
        tree = json.loads(r.read().decode("utf-8"))
    return [e["path"] for e in tree if e.get("type") == "directory"]

def download_candidate(out_path, max_per_subject=30, seed=42):
    import pyarrow.parquet as pq  # 延迟导入(仅 download 阶段需要)
    subjects = fetch_subjects()
    print(f"[download] 学科数={len(subjects)}", flush=True)
    rng = random.Random(seed)
    rows = []
    for sub in subjects:
        pq_url = f"{HF}/{sub}/val-00000-of-00001.parquet"
        try:
            req = urllib.request.Request(pq_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req) as r:
                raw = r.read()
            # 写临时 parquet 再读(避免 pyarrow 直接吃 bytes 的兼容问题)
            tmp = os.path.join(BENCH_DIR, f"_ceval_{sub}.parquet")
            with open(tmp, "wb") as f:
                f.write(raw)
            t = pq.read_table(tmp)
            recs = t.to_pylist()
            os.remove(tmp)
        except Exception as e:
            sys.stderr.write(f"[download] {sub} 拉取失败: {e}\n"); sys.stderr.flush()
            continue
        recs = recs[:max_per_subject] if len(recs) > max_per_subject else recs
        for rec in recs:
            q = (rec.get("question") or "").strip()
            ans = (rec.get("answer") or "").strip()
            opts = {k: (rec.get(k) or "").strip() for k in ("A", "B", "C", "D")}
            if not q or not ans or ans not in ("A", "B", "C", "D"):
                continue
            if not all(opts.values()):
                continue
            rows.append({
                "question": q, "A": opts["A"], "B": opts["B"],
                "C": opts["C"], "D": opts["D"],
                "answer": ans, "subject": rec.get("subject") or sub,
            })
        print(f"[download] {sub}: +{len(recs)} -> 累计 {len(rows)}", flush=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"[download] 候选池完成: {len(rows)} 题 -> {out_path}", flush=True)

def probe_and_filter(in_path, out_clean, out_probe, sample=None, seed=42):
    cfg = dict(V.DEFAULT_CFG)
    qs = [json.loads(l) for l in open(in_path, encoding="utf-8") if l.strip()]
    if sample and sample < len(qs):
        rng = random.Random(seed)
        qs = rng.sample(qs, sample)
    print(f"[probe] 探针 {len(qs)} 题, 模型 1.5B/3B/7B ...", flush=True)
    rows = []
    t0 = time.time()
    for i, q in enumerate(qs):
        try:
            a15 = S4.run_solo(q, cfg, "qwen2.5:1.5b")
        except Exception:
            a15 = None
        try:
            a3 = S4.run_solo(q, cfg, "qwen2.5:3b")
        except Exception:
            a3 = None
        try:
            a7 = S4.run_solo(q, cfg, "qwen2.5:7b")
        except Exception:
            a7 = None
        gold = q.get("answer")
        rows.append({**q, "a15": a15, "a3": a3, "a7": a7,
                     "ok_15b": a15 == gold, "ok_3b": a3 == gold, "ok_7b": a7 == gold})
        if (i + 1) % 10 == 0:
            el = (time.time() - t0) / 60
            sys.stderr.write(f"[probe] {i+1}/{len(qs)} elapsed={el:.1f}min\n"); sys.stderr.flush()

    kept, accs = make_band_ok(rows)
    band_ok = (accs["7b"] < 1.0) and (accs["3b"] > 0.25) and (accs["15b"] > 0.25)
    with open(out_clean, "w", encoding="utf-8") as f:
        for r in kept:
            f.write(json.dumps({k: r[k] for k in ("question", "A", "B", "C", "D", "answer", "subject")},
                               ensure_ascii=False) + "\n")
    probe = {
        "source": "C-Eval (hf-mirror/ceval/ceval-exam val)",
        "n_probed": len(rows), "n_kept": len(kept),
        "acc_15b": round(accs["15b"], 4), "acc_3b": round(accs["3b"], 4), "acc_7b": round(accs["7b"], 4),
        "band_ok": band_ok,
        "models": "qwen2.5:1.5b / 3b / 7b (DEFAULT_CFG)",
    }
    with open(out_probe, "w", encoding="utf-8") as f:
        json.dump(probe, f, ensure_ascii=False, indent=2)
    print(f"[probe] 完成: 探针 {len(rows)} 题 -> band_ok 子集 {len(kept)} 题", flush=True)
    print(f"[probe] acc: 1.5B={accs['15b']:.3f}  3B={accs['3b']:.3f}  7B={accs['7b']:.3f}  band_ok={band_ok}", flush=True)
    print(f"[probe] 产物: {out_clean} | {out_probe}", flush=True)

def compute_accs(rows):
    n = len(rows)
    return {
        "15b": sum(r["ok_15b"] for r in rows) / n,
        "3b": sum(r["ok_3b"] for r in rows) / n,
        "7b": sum(r["ok_7b"] for r in rows) / n,
    }

def make_band_ok(rows):
    rows = list(rows)
    while True:
        if len(rows) < 50:
            break
        a = compute_accs(rows)
        fails = []
        if a["7b"] >= 1.0:
            fails.append(("7b", True))    # 太强, 丢一个 7b 答对
        if a["3b"] <= 0.25:
            fails.append(("3b", False))   # 太弱, 丢一个 3b 答错
        if a["15b"] <= 0.25:
            fails.append(("15b", False))
        if not fails:
            break
        m, high = fails[0]
        cand = [r for r in rows if (r[f"ok_{m}"] if high else not r[f"ok_{m}"])]
        if not cand:
            break
        rows.remove(cand[0])
    return rows, compute_accs(rows)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--download", action="store_true", help="拉 C-Eval val -> 候选 pool jsonl")
    ap.add_argument("--probe", action="store_true", help="三模型探针 + band_ok 过滤")
    ap.add_argument("--out", default=os.path.join(BENCH_DIR, "ceval_candidate.jsonl"))
    ap.add_argument("--in", dest="in_path", default=os.path.join(BENCH_DIR, "ceval_candidate.jsonl"))
    ap.add_argument("--out-clean", default=os.path.join(BENCH_DIR, "ceval_bandok_clean.jsonl"))
    ap.add_argument("--out-probe", default=os.path.join(BENCH_DIR, "ceval_probe.json"))
    ap.add_argument("--max-per-subject", type=int, default=30)
    ap.add_argument("--sample", type=int, default=None, help="探针抽样题数(默认全部候选)")
    args = ap.parse_args()
    if args.download:
        download_candidate(args.out, max_per_subject=args.max_per_subject)
    elif args.probe:
        probe_and_filter(args.in_path, args.out_clean, args.out_probe, sample=args.sample)
    else:
        print("需指定 --download 或 --probe")
