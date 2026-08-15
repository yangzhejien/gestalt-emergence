#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
程序化生成多步推理 MCQ 题库 (≥100 道)，对 qwen2.5:1.5b 有真实区分度。
不依赖 ollama，纯本地确定性生成，避免出题模型偶发 hung。
输出: benchmark/mcq_hard100.jsonl  (每行 {question,A,B,C,D,answer})
"""
import json, random

random.seed(20260803)
OUT = r"D:\方程验证\benchmark\mcq_hard100.jsonl"


def make_options(correct, lo=-50, hi=600):
    opts = {correct}
    delta_pool = [-4, -3, -2, -1, 1, 2, 3, 4, 5, -5]
    while len(opts) < 4:
        d = correct + random.choice(delta_pool)
        if d != correct and lo <= d <= hi and d not in opts:
            opts.add(d)
    opts = list(opts)
    random.shuffle(opts)
    letter = "ABCD"[opts.index(correct)]
    return opts[0], opts[1], opts[2], opts[3], letter


def gen_arith():
    a = random.randint(2, 9); b = random.randint(2, 9)
    c = random.randint(2, 6); d = random.randint(1, 9); e = random.randint(2, 5)
    num = (a + b) * c - d
    if num <= 0 or num % e != 0:
        return None
    v = num // e
    q = f"计算 (({a}+{b})×{c}−{d})÷{e} 的值。"
    return q, v


def gen_word():
    a = random.randint(3, 12); b = random.randint(2, 8); c = random.randint(2, 6)
    total = a + (a + b) + (a + b) * c
    if total > 300:
        return None
    q = f"甲有{a}个，乙比甲多{b}个，丙的数量是乙的{c}倍。三人一共有多少个？"
    return q, total


def gen_logic():
    a = random.randint(5, 15)
    q = f"已知：X 比 Y 多 {a}，Y 比 Z 多 {a}。那么 X 比 Z 多多少？"
    return q, 2 * a


def gen_seq():
    t = random.choice(["arith", "geo", "second"])
    if t == "arith":
        d = random.randint(2, 5); s = random.randint(1, 5)
        seq = [s + d * i for i in range(5)]
        return f"数列 {seq} 的下一项是？", seq[-1] + d
    if t == "geo":
        r = random.randint(2, 3); s = random.randint(1, 4)
        seq = [s * r ** i for i in range(4)]
        return f"数列 {seq} 的下一项是？", seq[-1] * r
    d = random.randint(1, 3); s = random.randint(1, 4)
    seq = [s]
    for i in range(4):
        seq.append(seq[-1] + d * (i + 1))
    return f"数列 {seq} 的下一项是？", seq[-1] + d * 5


def gen_pct():
    a = random.randint(10, 40); b = random.randint(10, 30)
    v = round(100 * (1 + a / 100) * (1 - b / 100))
    q = f"某商品原价100元，先涨价{a}%，再降价{b}%，最终价格是多少？"
    return q, v


gens = [gen_arith, gen_word, gen_logic, gen_seq, gen_pct]
items, seen = [], set()
while len(items) < 100:
    r = random.choice(gens)()
    if not r:
        continue
    q, v = r
    if q in seen:
        continue
    seen.add(q)
    A, B, C, D, ans = make_options(v)
    items.append({"question": q, "A": A, "B": B, "C": C, "D": D, "answer": ans})

with open(OUT, "w", encoding="utf-8") as f:
    for it in items:
        f.write(json.dumps(it, ensure_ascii=False) + "\n")
print(f"wrote {len(items)} questions -> {OUT}")
