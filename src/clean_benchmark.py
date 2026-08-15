"""清洗 mcq_medium.jsonl -> mcq_medium_clean.jsonl
修复:
  1) __DUMMY3 占位符 -> 生成合理干扰项(数值题按正确值做算术扰动, 非数值题从全局池取异值)
  2) 每题 4 个选项字母随机重排(消除位置/字母偏见), 同步更新 answer
  3) 题目整体乱序(打散模板 clustering, 如 AVG3 全堆在 91-100)
输出 N=100 干净基准, 可复现(seed=20260804)。
"""
import json, random, re

SRC = r"D:/方程验证/benchmark/mcq_medium.jsonl"
DST = r"D:/方程验证/benchmark/mcq_medium_clean.jsonl"
SEED = 20260804
random.seed(SEED)

def is_num(s):
    try:
        float(str(s).replace(",", "")); return True
    except Exception:
        return False

def num(s):
    return float(str(s).replace(",", ""))

def make_distractor(opts, answer_val):
    """生成一个不等于正确答案、且不在现有选项中的干扰项。"""
    pool = []
    for b in [json.loads(l) for l in open(SRC, encoding="utf-8") if l.strip()]:
        for k in "ABCD":
            v = b.get(k, "")
            if "__DUMMY" not in str(v) and v not in opts and v != answer_val:
                pool.append(v)
    # 数值题: 优先用算术扰动产生贴近的干扰项
    if is_num(answer_val):
        a = num(answer_val)
        cands = [a * 1.5, a + 10, a * 0.5, a - 7, a * 2, a / 2]
        for c in cands:
            cs = (f"{c:.1f}".rstrip("0").rstrip(".") if c == int(c) else f"{c:.2f}")
            if cs not in opts and cs != answer_val:
                return cs
    if pool:
        return random.choice(pool)
    return "0"  # 极端兜底

bench = [json.loads(l) for l in open(SRC, encoding="utf-8") if l.strip()]
letters = ["A", "B", "C", "D"]
clean = []
for b in bench:
    opts = {k: b[k] for k in letters}
    # 1) 修 DUMMY
    for k in letters:
        if "__DUMMY" in str(opts[k]):
            opts[k] = make_distractor(list(opts.values()), b["answer"])
    # 2) 重排选项字母
    correct_val = opts[b["answer"]]  # 先取出正确值(字母指向的内容)
    vals = [opts[k] for k in letters]
    random.shuffle(vals)
    newb = {}
    ans_idx = vals.index(correct_val)  # 正确值在新排列中的位置
    for i, k in enumerate(letters):
        newb[k] = vals[i]
    newb["answer"] = letters[ans_idx]
    newb["question"] = b["question"]
    clean.append(newb)

# 3) 整体乱序
random.shuffle(clean)

with open(DST, "w", encoding="utf-8") as f:
    for b in clean:
        f.write(json.dumps(b, ensure_ascii=False) + "\n")

# 校验
dummy = [i + 1 for i, b in enumerate(clean) if "__DUMMY" in json.dumps(b)]
dist = {}
for b in clean:
    dist[b["answer"]] = dist.get(b["answer"], 0) + 1
print(f"written {len(clean)} questions -> {DST}")
print("remaining DUMMY:", dummy)
print("answer dist:", dist)
# 模板位置检查
def tmpl(q):
    if "average of" in q: return "AVG3"
    if "% of" in q: return "PCT"
    if "prime" in q: return "PRIME"
    return "OTHER"
from collections import defaultdict
pos = defaultdict(list)
for i, b in enumerate(clean):
    pos[tmpl(b["question"])].append(i + 1)
print("template positions:", {k: f"{v[0]}..{v[-1]}(n={len(v)})" for k, v in pos.items()})
