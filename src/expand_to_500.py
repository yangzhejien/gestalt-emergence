#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
扩基准到 500 题 (导师要求 N=500 以获得统计显著性)
================================================
在原始 100 题(mcq_medium_orig100.jsonl) 基础上, 程序化生成 400 道同分布
(初等数学应用题) MCQ, 正确项由构造计算保证, 干扰项取自常见错误/算术扰动。
随后覆盖写回 mcq_medium.jsonl(=100+400), 供 clean_benchmark.py 产出
mcq_medium_clean.jsonl(500 干净基准, 选项重排+整体乱序)。

设计约束(对应 sᵢ 前提 / 基准难度铁律):
  - 全为初等/初中难度, 英文应用题, 与现有 100 题同分布;
  - 不使用纯分数/符号题(避免 1.5B 贴地板), 概率改用百分数保持数值化;
  - 干扰项贴合常见错误, 保证题目有区分度但不过难。
"""
import json, random, os
from collections import Counter

SEED = 20260805
random.seed(SEED)
ROOT = "D:/方程验证/benchmark"
BACKUP = os.path.join(ROOT, "mcq_medium_orig100.jsonl")
SRC = os.path.join(ROOT, "mcq_medium.jsonl")
EXTRA = os.path.join(ROOT, "mcq_medium_extra400.jsonl")

def fmt(x):
    if abs(x - round(x)) < 1e-9:
        return str(int(round(x)))
    return f"{x:.1f}"

def build(correct_val, distractors):
    """correct_val: 数值或字符串; distractors: 同类型候选。返回 (options_dict, answer_letter)。"""
    opts = [correct_val]
    seen = {str(correct_val)}
    for d in distractors:
        if str(d) not in seen:
            seen.add(str(d)); opts.append(d)
    while len(opts) < 4:  # 极端兜底
        cand = fmt(float(correct_val) + len(opts) * 7)
        if cand not in seen:
            seen.add(cand); opts.append(cand)
    random.shuffle(opts)
    letters = ["A", "B", "C", "D"]
    d = {letters[i]: opts[i] for i in range(4)}
    ans = letters[opts.index(correct_val)]
    return d, ans

# ---------------- 模板库 (返回 (question, correct_str, [3 distractor_str])) ----------------
def t_discount():
    X = random.choice([40, 50, 60, 80, 100, 120, 150, 200, 240, 300])
    Y = random.choice([10, 15, 20, 25, 30, 40])
    c = X * (1 - Y / 100)
    return (f"A ${X} item is on sale for {Y}% off. What is the sale price in dollars?",
            fmt(c), [fmt(X * Y / 100), fmt(X / (1 - Y / 100)), fmt(X * (1 + Y / 100))])

def t_speed():
    T = random.choice([2, 3, 4, 5, 6, 7, 8])
    sp = random.choice([30, 40, 50, 60, 70, 80, 90])
    D = T * sp
    return (f"A car travels {D} km in {T} hours. What is its average speed in km/h?",
            fmt(sp), [fmt(D * T), fmt(D + T), fmt(D / T if T < D else T / D)])

def t_algebra():
    b = random.choice([1, 3, 5, 7, 9, 11, 13])
    x = random.choice([2, 3, 4, 5, 6, 7, 8, 9])
    c = 2 * x + b
    return (f"Solve for x: 2x + {b} = {c}.",
            fmt(x), [fmt(c - b), fmt((c + b) // 2), fmt(c // 2 - b)])

def t_area():
    L = random.choice([6, 7, 8, 9, 10, 12, 15, 18])
    W = random.choice([4, 5, 6, 7, 8, 9, 10])
    return (f"A rectangle has length {L} and width {W}. What is its area?",
            fmt(L * W), [fmt(L + W), fmt(2 * (L + W)), fmt(L * W / 2)])

def t_pct():
    X = random.choice([80, 120, 150, 200, 250, 300, 360])
    P = random.choice([10, 15, 20, 25, 40, 50])
    return (f"What is {P}% of {X}?",
            fmt(X * P / 100), [fmt(X * (100 - P) / 100), fmt(X + P), fmt(X - P)])

def t_avg3():
    a = random.choice([10, 12, 14, 15, 18, 20, 25])
    b = random.choice([22, 24, 25, 28, 30, 35])
    c = random.choice([32, 35, 36, 40, 42, 45])
    return (f"What is the average of {a}, {b}, and {c}?",
            fmt((a + b + c) / 3), [fmt(a + b + c), fmt((a + b + c) / 2), fmt(max(a, b, c))])

# ---- 新增模板 (保持初等, 数值化) ----
def t_combo():
    n = random.choice([4, 5, 6, 7, 8, 9])
    c = n * (n - 1) // 2
    return (f"How many ways are there to choose 2 items from {n} distinct items?",
            fmt(c), [fmt(n * (n - 1)), fmt(n * (n + 1) // 2), fmt(n * n - 1)])

def t_power():
    a = random.choice([2, 3, 4]); b = random.choice([3, 4, 5])
    c = a ** b
    return (f"What is {a}^{b}?",
            fmt(c), [fmt(a * b), fmt(a + b), fmt(a * b - 1)])

def t_unit():
    kind = random.choice(["km_m", "m_cm", "kg_g", "L_mL"])
    if kind == "km_m":
        v = random.choice([2, 3, 5, 7, 9]); return (f"How many meters are in {v} kilometers?", fmt(v * 1000), [fmt(v), fmt(v * 100), fmt(v * 10)])
    if kind == "m_cm":
        v = random.choice([3, 5, 7, 12, 15]); return (f"How many centimeters are in {v} meters?", fmt(v * 100), [fmt(v), fmt(v * 10), fmt(v * 1000)])
    if kind == "kg_g":
        v = random.choice([2, 4, 6, 8]); return (f"How many grams are in {v} kilograms?", fmt(v * 1000), [fmt(v), fmt(v * 100), fmt(v * 10)])
    v = random.choice([2, 3, 5]); return (f"How many milliliters are in {v} liters?", fmt(v * 1000), [fmt(v * 100), fmt(v * 10), fmt(v)])

def t_interest():
    P = random.choice([100, 200, 500, 1000]); r = random.choice([5, 10, 15, 20]); t = random.choice([1, 2, 3])
    c = P * r * t / 100
    return (f"A sum of ${P} is invested at {r}% simple interest per year for {t} years. What is the total interest earned in dollars?",
            fmt(c), [fmt(P * r / 100), fmt(P * t), fmt(P * r * t)])

def t_prop():
    a = random.choice([3, 4, 5, 6]); B = random.choice([9, 12, 15, 20, 24]); C = random.choice([7, 8, 9, 10, 12])
    c = B * C / a
    return (f"If {a} apples cost ${B}, how much do {C} apples cost at the same rate?",
            fmt(c), [fmt(B / a), fmt(B + C), fmt(a * C)])

def t_work():
    a = random.choice([4, 6, 8, 10, 12]); b = random.choice([6, 8, 10, 12, 15])
    c = a * b / (a + b)
    return (f"Worker A can finish a job in {a} days. Worker B can finish it in {b} days. Working together, how many days do they need?",
            fmt(c), [fmt(a + b), fmt((a + b) / 2), fmt(a * b)])

def t_seq():
    d = random.choice([2, 3, 4, 5]); s = random.choice([1, 3, 5, 7])
    seq = [s + d * i for i in range(4)]
    c = seq[-1] + d
    return (f"What is the next number in the sequence {seq}?",
            fmt(c), [fmt(seq[-1] + 2 * d), fmt(seq[-1] - d), fmt(s + d)])

def t_age():
    a = random.choice([3, 5, 7, 9, 11]); b = random.choice([2, 4, 6, 8, 10])
    return (f"Tom is {a} years older than Lily. Lily is {b} years older than Max. How many years older is Tom than Max?",
            fmt(a + b), [fmt(a), fmt(b), fmt(a - b)])

def t_perim():
    L = random.choice([6, 7, 8, 9, 10, 12]); W = random.choice([4, 5, 6, 7, 8, 9])
    return (f"A rectangle has length {L} and width {W}. What is its perimeter?",
            fmt(2 * (L + W)), [fmt(L + W), fmt(L * W), fmt(4 * (L + W))])

def t_volume():
    L = random.choice([3, 4, 5, 6]); W = random.choice([3, 4, 5]); H = random.choice([2, 3, 4, 5])
    return (f"A rectangular box has length {L}, width {W}, height {H}. What is its volume?",
            fmt(L * W * H), [fmt(L + W + H), fmt(2 * (L + W + H)), fmt(L * W)])

def t_pctchange():
    P = random.choice([80, 100, 120, 200]); r = random.choice([10, 20, 25, 50])
    return (f"A price of ${P} increases by {r}%. What is the new price?",
            fmt(P * (1 + r / 100)), [fmt(P * r / 100), fmt(P - P * r / 100), fmt(P * (1 - r / 100))])

def t_prob():
    R = random.choice([2, 3, 4, 5]); B = random.choice([3, 4, 5, 6])
    tot = R + B
    return (f"A bag has {R} red and {B} blue marbles. What is the percent chance of drawing a red marble?",
            fmt(R / tot * 100), [fmt(B / tot * 100), fmt(R / B * 100), fmt(tot / R * 100)])

def t_div():
    N = random.choice([20, 24, 30, 36, 42, 48]); K = random.choice([3, 4, 5, 6, 7, 8])
    return (f"What is the integer quotient when {N} is divided by {K} (ignore remainder)?",
            fmt(N // K), [fmt(N * K), fmt(N - K), fmt(N % K)])

TEMPLATES = [t_discount, t_speed, t_algebra, t_area, t_pct, t_avg3,
             t_combo, t_power, t_unit, t_interest, t_prop, t_work,
             t_seq, t_age, t_perim, t_volume, t_pctchange, t_prob, t_div]
# 注: 19 个模板, 每模板 21 题 -> 399, 再补 1 题到 400
PER = 21
N_EXTRA = PER * len(TEMPLATES) + 1

extra = []
seen_q = set()
tname = {t.__name__: t for t in TEMPLATES}
# 轮询各模板生成
idx = 0
while len(extra) < N_EXTRA:
    t = TEMPLATES[idx % len(TEMPLATES)]
    idx += 1
    q, correct, dist = t()
    if q in seen_q:
        continue
    seen_q.add(q)
    d, ans = build(correct, dist)
    extra.append({"question": q, **d, "answer": ans, "_tpl": t.__name__})

# 写入额外 400
with open(EXTRA, "w", encoding="utf-8") as f:
    for it in extra:
        f.write(json.dumps(it, ensure_ascii=False) + "\n")

# 合并原始 100 + 额外 400 -> 覆盖写回 SRC (幂等)
orig = [json.loads(l) for l in open(BACKUP, encoding="utf-8") if l.strip()]
merged = orig + [{k: v for k, v in it.items() if k != "_tpl"} for it in extra]
with open(SRC, "w", encoding="utf-8") as f:
    for it in merged:
        f.write(json.dumps(it, ensure_ascii=False) + "\n")

# 统计
cnt_tpl = Counter(it["_tpl"] for it in extra)
cnt_ans = Counter(it["answer"] for it in extra)
print(f"生成额外题: {len(extra)} (目标 {N_EXTRA})")
print(f"原始 {len(orig)} + 额外 = 写回 SRC 总行数: {len(merged)}")
print("模板分布:", dict(cnt_tpl))
print("额外题答案字母分布:", dict(cnt_ans))
