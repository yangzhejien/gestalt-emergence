#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P0 难度画像: 测单模型(1.5B/3B/7B)在某 MCQ 题库上的 solo 准确率,
定位"更高难基准"的目标区间:
  强模型(7B) solo 落 0.45~0.65 (给 ΣαₘẆ²ᵐ 留显示余量)
  最弱(1.5B) solo > 0.40   (保 sᵢ>0 地板, 否则 M≈0+干扰)
  每层 sᵢ > 0.25         (铁律: 任一节点不能贴随机)
复用 verify_stage2 的 generate/build_l3/extract_choice, 与正式运行同口径。
用法:
  python scan_solo_accuracy.py --bench benchmark/mcq_hard_pool.jsonl --n 50
"""
import json, random, sys, argparse
sys.path.insert(0, "D:/方程验证/scripts")
from verify_stage2 import DEFAULT_CFG, generate, build_l3, extract_choice

PERSONA = "You are a careful general expert."


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", required=True)
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--seed", type=int, default=20260808)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    cfg = dict(DEFAULT_CFG)
    random.seed(args.seed)
    qs = [json.loads(l) for l in open(args.bench, encoding="utf-8") if l.strip()]
    n = min(args.n, len(qs))
    sample = random.sample(qs, n)
    for i, q in enumerate(sample):
        q.setdefault("id", f"s{i+1}")

    models = {
        "l3_1.5b": cfg["l3_model"],
        "l2_3b": cfg["agg_model"],
        "l1_7b": cfg["l1_model"],
    }

    results = {}
    for key, model in models.items():
        ans = []
        for ti, q in enumerate(sample):
            try:
                a = extract_choice(generate(build_l3(q, PERSONA), "expert", cfg, model=model))
            except Exception as e:
                a = None
                sys.stderr.write(f"[{key}] q{ti+1} err {e}\n"); sys.stderr.flush()
            ans.append(a)
            sys.stderr.write(f"[{key}] q {ti+1}/{n}\n"); sys.stderr.flush()
        valid = [a for a in ans if a is not None]
        acc = sum(1 for a, q in zip(ans, sample) if a == q["answer"]) / n
        results[key] = round(acc, 4)
        print(f"{key}: acc={acc:.3f} (valid {len(valid)}/{n})", flush=True)

    print("SUMMARY " + json.dumps(results, ensure_ascii=False), flush=True)
    if args.out:
        json.dump({"bench": args.bench, "n": n, "results": results},
                  open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print("-> " + args.out, flush=True)


if __name__ == "__main__":
    main()
