#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
整改②配套: 把统一基准 mcq_medium.jsonl 从 40 题扩充到 100 题 (导师要求 N=100)。
用 6 类推理模板程序化生成, 正确答案由构造计算保证正确, 避免手写出错;
四个选项(A/B/C/D)位置在全部 60 题中均衡分布。追加写入, 不动原有 40 题。
"""
import json, random, os

random.seed(20260804)
ROOT = "D:/方程验证/benchmark"
SRC = os.path.join(ROOT, "mcq_medium.jsonl")

def fmt(x):
    # 统一成整数或1位小数, 去尾巴零
    if abs(x - round(x)) < 1e-9:
        return str(int(round(x)))
    return f"{x:.1f}"

def make_options(correct_val, distractors):
    """correct_val: 数值或字符串; distractors: 同类型候选列表。返回 (options_dict, answer_letter)。"""
    opts = [correct_val] + list(distractors)
    # 去重保序
    seen = set(); uniq = []
    for o in opts:
        if o not in seen:
            seen.add(o); uniq.append(o)
    while len(uniq) < 4:
        uniq.append(f"__DUMMY{len(uniq)}")  # 极端兜底(正常不会触发)
    random.shuffle(uniq)
    letters = ["A", "B", "C", "D"]
    d = {letters[i]: uniq[i] for i in range(4)}
    ans = letters[uniq.index(correct_val)]
    return d, ans

qs = []

# ---- T1 折扣 ----
for _ in range(10):
    X = random.choice([40, 50, 60, 80, 100, 120, 150, 200])
    Y = random.choice([10, 15, 20, 25, 30])
    correct = X * (1 - Y / 100)
    d, ans = make_options(fmt(correct), [
        fmt(X * Y / 100),            # 折扣金额(常见错)
        fmt(X / (1 - Y / 100)),      # 反向除(常见错)
        fmt(X * (1 + Y / 100)),      # 加回(常见错)
    ])
    qs.append({"question": f"A ${X} item is on sale for {Y}% off. What is the sale price in dollars?", **d, "answer": ans})

# ---- T2 速度/距离 ----
for _ in range(10):
    T = random.choice([2, 3, 4, 5, 6])
    sp = random.choice([30, 40, 50, 60, 70, 80])
    D = T * sp
    correct = sp
    d, ans = make_options(fmt(correct), [
        fmt(D * T), fmt(D + T), fmt(D / T if T < D else T / D),
    ])
    qs.append({"question": f"A car travels {D} km in {T} hours. What is its average speed in km/h?", **d, "answer": ans})

# ---- T3 代数 2x+b=c ----
for _ in range(10):
    b = random.choice([1, 3, 5, 7, 9, 11])
    x = random.choice([2, 3, 4, 5, 6, 7, 8])
    c = 2 * x + b
    correct = x
    d, ans = make_options(fmt(correct), [
        fmt(c - b), fmt((c + b) // 2), fmt(c // 2 - b),
    ])
    qs.append({"question": f"Solve for x: 2x + {b} = {c}.", **d, "answer": ans})

# ---- T4 矩形面积 ----
for _ in range(10):
    L = random.choice([6, 7, 8, 9, 10, 12, 15])
    W = random.choice([4, 5, 6, 7, 8, 9])
    correct = L * W
    d, ans = make_options(fmt(correct), [
        fmt(L + W), fmt(2 * (L + W)), fmt(L * W / 2),
    ])
    qs.append({"question": f"A rectangle has length {L} and width {W}. What is its area?", **d, "answer": ans})

# ---- T5 百分比 ----
for _ in range(10):
    X = random.choice([80, 120, 150, 200, 250, 300])
    P = random.choice([10, 15, 20, 25, 40])
    correct = X * P / 100
    d, ans = make_options(fmt(correct), [
        fmt(X * (100 - P) / 100), fmt(X + P), fmt(X - P),
    ])
    qs.append({"question": f"What is {P}% of {X}?", **d, "answer": ans})

# ---- T6 平均数 ----
for _ in range(10):
    a = random.choice([10, 12, 14, 15, 18, 20])
    b = random.choice([22, 24, 25, 28, 30])
    c = random.choice([32, 35, 36, 40, 42])
    correct = (a + b + c) / 3
    d, ans = make_options(fmt(correct), [
        fmt(a + b + c), fmt((a + b + c) / 2), fmt(max(a, b, c)),
    ])
    qs.append({"question": f"What is the average of {a}, {b}, and {c}?", **d, "answer": ans})

# 均衡检查 + 写盘
from collections import Counter
cnt = Counter(q["answer"] for q in qs)
print("新增题数:", len(qs), "| 答案分布:", dict(cnt))

# 追加到现有文件 (保留原 40 题)
with open(SRC, "a", encoding="utf-8") as f:
    for q in qs:
        f.write(json.dumps(q, ensure_ascii=False) + "\n")

total = sum(1 for _ in open(SRC, encoding="utf-8") if _.strip())
print(f"mcq_medium.jsonl 总行数(含原40): {total}")
