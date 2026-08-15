#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""诊断 hard_pool 里 3B 是否真错还是解析失败: 打印单题原始输出."""
import json, sys
sys.path.insert(0, "D:/方程验证/scripts")
from verify_stage2 import DEFAULT_CFG, generate, build_l3, extract_choice

cfg = dict(DEFAULT_CFG)
PERSONA = "You are a careful general expert."
qs = [json.loads(l) for l in open("benchmark/mcq_hard_pool.jsonl", encoding="utf-8") if l.strip()]
q = qs[0]
print("=== 题目 ===")
print(json.dumps(q, ensure_ascii=False)[:600])
for label, model in [("1.5B", cfg["l3_model"]), ("3B", cfg["agg_model"]), ("7B", cfg["l1_model"])]:
    try:
        raw = generate(build_l3(q, PERSONA), "expert", cfg, model=model)
    except Exception as e:
        raw = f"<EXC {e}>"
    print(f"\n=== {label} 原始输出(前400) ===")
    print(repr(raw[:400]) if raw else repr(raw))
    print(f"  extract_choice -> {extract_choice(raw) if raw else None}")
    print(f"  gold={q.get('answer')}")
