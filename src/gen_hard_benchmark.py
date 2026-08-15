#!/usr/bin/env python3
# gen_hard_benchmark.py — 生成"更高难度" MCQ 基准(给超线性项留上升余量)
# ─────────────────────────────────────────────────────────────────
# 目标难度带(方程物理前提): 强模型(7B) solo 落 0.45~0.65(远低于当前0.83的天花板,
#   给 ΣαₘẆ²ᵐ 留显示空间); 最弱(1.5B) solo > 0.40(保 sᵢ>0 地板, 否则 M≈0+干扰)。
# 方法: 用 7B 批量生成"需多步推理/精确计算/强干扰项"的难题, 解析校验后落池, 可断点续跑。
# 用法: python gen_hard_benchmark.py --target 250
# ─────────────────────────────────────────────────────────────────
import sys, os, json, re, argparse, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify_stage2 as V
generate = V.generate
DEFAULT_CFG = V.DEFAULT_CFG
ROOT = V.ROOT

CREATOR = "qwen2.5:7b"
POOL_PATH = ROOT / "benchmark" / "mcq_hard_pool.jsonl"
TARGET = 250
BATCH = 4  # 每次生成题数(小一点利于 JSON 解析)

SYSTEM = (
    "You are a rigorous math & logic test designer. Create HARD multiple-choice questions that "
    "test PURE REASONING DEPTH — genuine multi-step deduction, calculation, and logical chains — "
    "and NOTHING that depends on factual knowledge, trivia, memorization, or domain/subject "
    "breadth. Each question MUST require at least 2-3 steps of reasoning (arithmetic/word "
    "problems, algebra, combinatorics, conditional logic, probability that needs real computation). "
    "A capable 7B model should answer only about 50-60% correctly, because the distractors are "
    "built from GENUINE common mistakes (wrong operation order, sign errors, off-by-one, "
    "misapplied formula, inverted conditional) — never random or obviously-wrong numbers. No "
    "question may be solvable by recall or general knowledge alone. Exactly one correct option "
    "among A/B/C/D; keep it self-contained (Chinese or English). "
    "IMPORTANT difficulty calibration: create a REASONING-DEPTH gap, not a hard "
    "knowledge gap. A 3B model should answer correctly about 30-40% of the time "
    "(never near 0%), and a 1.5B model about 25-35%. The trap must be a step a 7B "
    "sometimes slips on, not something only 7B can even parse."
)

def build_prompt(n):
    return (
        f"Generate {n} HARD reasoning questions (PURE reasoning only — no factual/trivia/knowledge "
        "breadth, no lookup-by-memory). Output ONLY a JSON array, no prose, each element:\n"
        '[{"q":"<question text>",'
        '"options":{"A":"<opt>","B":"<opt>","C":"<opt>","D":"<opt>"},'
        '"answer":"<A|B|C|D>","rationale":"<why correct, mention the key reasoning step>",'
        '"common_error":"<the mistake that leads to the WRONG but plausible distractor>"}, ...]\n'
        "Hard rules: (1) every question needs 2-3+ steps of reasoning, never a one-step lookup; "
        "(2) at least two distractors must be the RESULT of a REAL error a reasoner makes "
        "(arithmetic slip, wrong formula, sign flip, swapped variables, inverted condition) — "
        "these are the traps; (3) no question answerable from memory or general knowledge alone; "
        "(4) answer matches exactly one option."
    )

def parse_batch(text):
    if not text:
        return []
    # 去除 markdown 围栏(```json / ```), 容忍 7B 加 prose 包裹
    cleaned = re.sub(r"```(?:json)?", "", text, flags=re.I).replace("```", "")
    # 7B 常以 LaTeX 数学分隔符 \( \) \[ \] 输出, 其中反斜杠不是合法 JSON 转义,
    # 会导致 raw_decode 抛错 -> 整批解析为空. 先剥离"非法反斜杠转义"(保留 \\ \" \/ \b \f \n \r \t \u 等合法项).
    cleaned = re.sub(r'\\(?!["\\/bfnrtu])', '', cleaned)
    start = cleaned.find("[")
    if start < 0:
        return []
    # 从首个 [ 起用 raw_decode 解析数组, 容忍尾随非 JSON 文本(如 7B 的收尾说明)
    try:
        arr, _ = json.JSONDecoder().raw_decode(cleaned[start:])
    except Exception:
        return []
    if not isinstance(arr, list):
        return []
    out = []
    for it in arr:
        if not isinstance(it, dict):
            continue
        q = (it.get("q") or "").strip()
        opts = it.get("options") or {}
        if not q or not isinstance(opts, dict):
            continue
        letters = [k.upper() for k in opts.keys() if k.upper() in "ABCD"]
        if len(letters) != 4:
            continue
        ans = (str(it.get("answer") or "").strip().upper())
        if ans not in "ABCD":
            continue
        if ans not in letters:
            continue
        out.append({
            "q": q,
            "options": {L: str(opts[L]).strip() for L in "ABCD"},
            "answer": ans,
            "rationale": (it.get("rationale") or "").strip(),
        })
    return out

def count_existing():
    if not POOL_PATH.exists():
        return 0
    n = 0
    for line in open(POOL_PATH, encoding="utf-8"):
        if line.strip():
            n += 1
    return n

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=TARGET)
    ap.add_argument("--creator", default=CREATOR)
    args = ap.parse_args()

    cfg = dict(DEFAULT_CFG)
    have = count_existing()
    print(f"[gen_hard] pool={POOL_PATH} existing={have} target={args.target}", flush=True)
    if have >= args.target:
        print("[gen_hard] 已达目标, 退出"); return

    # warmup creator
    try:
        V.warmup_models(cfg)
    except Exception as e:
        print("[gen_hard] warmup warn:", e, flush=True)

    created = have
    attempts = 0
    while created < args.target and attempts < args.target * 3:
        attempts += 1
        remain = min(BATCH, args.target - created)
        try:
            txt = generate(build_prompt(remain), SYSTEM, cfg, model=args.creator, max_tokens=3072)
        except Exception as e:
            print("[gen_hard] gen err:", e, flush=True); time.sleep(2); continue
        items = parse_batch(txt)
        if not items:
            print(f"[gen_hard] batch parse empty (attempt {attempts})", flush=True); continue
        with open(POOL_PATH, "a", encoding="utf-8") as f:
            for it in items:
                f.write(json.dumps(it, ensure_ascii=False) + "\n")
        created += len(items)
        print(f"[gen_hard] +{len(items)} -> pool={created}/{args.target}", flush=True)
        time.sleep(0.3)

    print(f"[gen_hard] DONE pool={count_existing()} path={POOL_PATH}", flush=True)

if __name__ == "__main__":
    main()
