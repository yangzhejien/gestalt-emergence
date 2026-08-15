#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
难度探针(闸门): 在扩后的 500 基准上随机抽 40 题, 跑 5 个单模型 solo,
确认 sᵢ 前提不被破坏:
  - 1.5B 集群均值 > 0.40 (不贴地板)
  - 7B 最强单体 < 0.98 (留余量, 未到天花板)
复用 verify_stage2 的 generate/build_l3/extract_choice, 保证与正式运行同口径。
"""
import json, random, sys
sys.path.insert(0, "D:/方程验证/scripts")
from verify_stage2 import DEFAULT_CFG, generate, build_l3, extract_choice

BENCH = "D:/方程验证/benchmark/mcq_medium_clean.jsonl"
SEED = 20260805
N_SAMPLE = 40

random.seed(SEED)
questions = [json.loads(l) for l in open(BENCH, encoding="utf-8") if l.strip()]
sample = random.sample(questions, N_SAMPLE)
for i, q in enumerate(sample):
    q.setdefault("id", f"probe{i+1}")

cfg = dict(DEFAULT_CFG)
models = {
    "l3_0": (cfg["l3_model"], cfg["l3_personas"][0]),
    "l3_1": (cfg["l3_model"], cfg["l3_personas"][1]),
    "l3_2": (cfg["l3_model"], cfg["l3_personas"][2]),
    "l2_3b": (cfg["agg_model"], "You are a careful general expert."),
    "l1_7b": (cfg["l1_model"], "You are a careful general expert."),
}

results = {}
for key, (model, persona) in models.items():
    ans = []
    for ti, q in enumerate(sample):
        ans.append(extract_choice(generate(build_l3(q, persona), "expert", cfg, model=model)))
        sys.stderr.write(f"[{key}] q {ti+1}/{N_SAMPLE}\n"); sys.stderr.flush()
    acc = sum(1 for a, q in zip(ans, sample) if a == q["answer"]) / len(sample)
    results[key] = round(acc, 4)
    print(f"{key}: acc={acc:.3f}")

l3_avg = sum(results[f"l3_{i}"] for i in range(3)) / 3
best = max(results.values())
print(f"\n1.5B 集群均值 = {l3_avg:.3f}  | 最强单体(7b) = {results['l1_7b']:.3f}  | 3b = {results['l2_3b']:.3f}")
verdict = []
verdict.append("PASS 1.5B>0.40" if l3_avg > 0.40 else "FAIL 1.5B 贴地板")
verdict.append("PASS 7b<0.98" if results["l1_7b"] < 0.98 else "FAIL 7b 触顶")
print("闸门:", " & ".join(verdict))

json.dump({"n_sample": N_SAMPLE, "results": results, "l3_avg": round(l3_avg, 4),
           "verdict": verdict}, open("D:/方程验证/benchmark/probe_result.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print("-> D:/方程验证/benchmark/probe_result.json")
