#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P0 基准筛选: 从 hard_pool(大模型生成的难题池) 逐题测 1.5B/3B/7B solo,
随机搜索选出一个子集, 使基准整体落入目标难度带(方程物理前提):
    7B 均值 ≈ 0.55  (最强单体留余量, 给 ΣαₘẆ²ᵐ 显示空间)
    3B 均值 > 0.25  (铁律: 每层 sᵢ>0.25 地板)
    1.5B 均值 > 0.25 (同上)
用法:
  python build_hard_clean.py --pool benchmark/mcq_hard_pool.jsonl --target 250
"""
import json, sys, argparse, random, statistics
sys.path.insert(0, "D:/方程验证/scripts")
from verify_stage2 import DEFAULT_CFG, generate, build_l3, extract_choice

PERSONA = "You are a careful general expert."


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pool", default="benchmark/mcq_hard_pool.jsonl")
    ap.add_argument("--target", type=int, default=250)
    ap.add_argument("--out", default="benchmark/mcq_hard2_clean.jsonl")
    ap.add_argument("--searches", type=int, default=3000)
    ap.add_argument("--seed", type=int, default=20260808)
    args = ap.parse_args()

    cfg = dict(DEFAULT_CFG)
    qs = [json.loads(l) for l in open(args.pool, encoding="utf-8") if l.strip()]
    print(f"[build] pool={len(qs)} target={args.target}", flush=True)
    if len(qs) < args.target:
        print("[build] WARN pool < target, 将退化为使用全部", flush=True)

    models = {"l3_1.5b": cfg["l3_model"], "l2_3b": cfg["agg_model"], "l1_7b": cfg["l1_model"]}
    # 逐题测三模型 solo
    per = {}
    for i, q in enumerate(qs):
        rec = {}
        for key, model in models.items():
            try:
                a = extract_choice(generate(build_l3(q, PERSONA), "expert", cfg, model=model))
            except Exception:
                a = None
            rec[key] = 1 if a == q["answer"] else 0
        per[i] = rec
        sys.stderr.write(f"q{i+1}/{len(qs)} {rec}\n"); sys.stderr.flush()

    # 随机搜索最优子集
    random.seed(args.seed)
    n_pool = len(qs)
    tgt = min(args.target, n_pool)
    best = None
    best_d = 1e9
    for _ in range(args.searches):
        idxs = random.sample(range(n_pool), tgt)
        m7 = statistics.mean(per[i]["l1_7b"] for i in idxs)
        m3 = statistics.mean(per[i]["l2_3b"] for i in idxs)
        m15 = statistics.mean(per[i]["l3_1.5b"] for i in idxs)
        if m3 < 0.25 or m15 < 0.25:
            continue
        d = abs(m7 - 0.55)
        if d < best_d:
            best_d = d
            best = (idxs, m7, m3, m15)
    if best is None:
        print("[build] FAIL 找不到满足地板的子集, 需扩充/重生成 pool", flush=True)
        return
    idxs, m7, m3, m15 = best
    with open(args.out, "w", encoding="utf-8") as f:
        for i in idxs:
            f.write(json.dumps(qs[i], ensure_ascii=False) + "\n")
    print(f"[build] selected {len(idxs)} -> {args.out}", flush=True)
    print(f"[build] subset means: 7B={m7:.3f} 3B={m3:.3f} 1.5B={m15:.3f}  (目标 7B~0.55, 地板>0.25)",
          flush=True)
    json.dump({"n": len(idxs),
               "means": {"7B": round(m7, 4), "3B": round(m3, 4), "1.5B": round(m15, 4)},
               "per": per},
              open(args.out.replace(".jsonl", ".stats.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"[build] -> {args.out.replace('.jsonl', '.stats.json')}", flush=True)


if __name__ == "__main__":
    main()
