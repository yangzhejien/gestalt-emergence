#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
整改第一步: 排查 3B 模型反常偏弱 (导师批评④)
============================================
导师指出 T3/rep1 中 3B(abliterate:3b) solo 准确率(43%/52.5%) 低于 1.5B(53~67%), 反常。
根因嫌疑: 主实验 1.5B 用原版 qwen2.5:1.5b, 而 3B/7B 用 abliterate 版 -> 版本混用。

本脚本在 mcq_medium 上对比:
  abliterate:3b  vs  原版 qwen2.5:3b      (隔离 abliterate 效应, 同尺度 3B)
  abliterate:1.5b vs 原版 qwen2.5:1.5b    (同尺度 1.5B 对照组, 验证 abliterate 是否系统性掉点)

复用 verify_stage2 的 build_l3 + extract_choice + generate, 保证测评方式与主实验一致、模型间可比。
"""
import sys, json, time, urllib.request
sys.path.insert(0, r"D:/方程验证/scripts")
import verify_stage2 as V
from pathlib import Path

cfg = dict(V.DEFAULT_CFG)
cfg["temperature"] = 0.0
cfg["benchmark"] = "benchmark/mcq_medium.jsonl"
bench_path = V.ROOT / cfg["benchmark"]
questions = [json.loads(l) for l in open(bench_path, encoding="utf-8") if l.strip()]
N = min(len(questions), 40)          # 用 40 题, 与 rep1 对齐
questions = questions[:N]
print(f"[probe] benchmark={bench_path.name} n={N}", flush=True)

MODELS = {
    "abliterate:3b":   "huihui_ai/qwen2.5-abliterate:3b",
    "qwen2.5:3b_orig": "qwen2.5:3b",
    "abliterate:1.5b": "huihui_ai/qwen2.5-abliterate:1.5b",
    "qwen2.5:1.5b_orig": "qwen2.5:1.5b",
}

def ollama_models():
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=10) as r:
            return [m["name"] for m in json.loads(r.read()).get("models", [])]
    except Exception as e:
        print(f"[probe] tags err {e}", flush=True)
        return []

def wait_model(name, timeout=1500):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if any(name == m or m.startswith(name + ":") for m in ollama_models()):
            return True
        time.sleep(30)
    return False

results = {}
for label, m in MODELS.items():
    installed = any(m == x or x.startswith(m + ":") for x in ollama_models())
    if not installed:
        print(f"[probe] {label} 未安装, 等待 pull(最多25分钟)...", flush=True)
        if not wait_model(m):
            print(f"[probe] {label} 超时未装, 跳过", flush=True)
            results[label] = None
            continue
    print(f"[probe] 测 {label} ({m}) ...", flush=True)
    ans = []
    for i, q in enumerate(questions):
        # 与主实验 solo 完全一致: build_l3 + system='expert'
        r = V.generate(V.build_l3(q, "You are a careful general expert."),
                       "expert", cfg, model=m)
        ans.append(V.extract_choice(r))
        if (i + 1) % 10 == 0:
            print(f"  {label} {i+1}/{N}", flush=True)
    acc = sum(1 for a, q in zip(ans, questions) if a == q["answer"]) / N
    results[label] = round(acc, 4)
    print(f"[probe] {label} solo_acc={acc:.3f}", flush=True)

out = V.OUT / "probe_3b_result.json"
out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"[probe] DONE -> {out}", flush=True)
print(json.dumps(results, ensure_ascii=False), flush=True)
