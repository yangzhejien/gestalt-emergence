#!/usr/bin/env python3
# gen_midhard_benchmark.py — 生成"中高难度" MCQ 基准
# ─────────────────────────────────────────────────────────────────
# 目的: 修复 hard 基准违反的"升级版难度铁律"——每一层 sᵢ 都须 > 随机(>0.25),
#   且最强(7B) 不贴天花板(给 ΣαₘẆ²ᵐ 留显示空间)。
# 目标难度带: 7B solo ∈ [0.60,0.72] (留头顶空间但不过难把超线性项也压没)
#             3B solo > 0.25      (中层 L2 须有实值, 不能像 hard 那样崩到 3%)
#             1.5B solo > 0.30    (最弱节点保地板)
# 方法: 7B 生成 1-2 步推理+单陷阱的中难题, 解析校验后落池(带 LaTeX 反斜杠修复)。
# 用法: python gen_midhard_benchmark.py --target 250
# ─────────────────────────────────────────────────────────────────
import sys, os, json, re, argparse, time
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify_stage2 as V
generate = V.generate
DEFAULT_CFG = V.DEFAULT_CFG
ROOT = V.ROOT

CREATOR = "qwen2.5:7b"
POOL_PATH = ROOT / "benchmark" / "mcq_midhard_pool.jsonl"
LIVE_PATH = Path(r"C:\Users\11409\WorkBuddy\2026-07-28-21-49-24\gestalt_live\midhard_live.json")
TARGET = 250
BATCH = 4  # 每次生成题数(小一点利于 JSON 解析)

def write_live(d, live_path=LIVE_PATH):
    """原子写 live(看板只读此文件); tmp+replace 防半写导致浏览器 JSON 解析失败。"""
    try:
        tmp = str(live_path) + ".tmp"
        open(tmp, "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=False))
        os.replace(tmp, str(live_path))
    except Exception:
        pass

SYSTEM = (
    "You are a rigorous math & logic test designer. Create MODERATELY HARD multiple-choice "
    "questions that test reasoning with SOME computation, but stay at 1-2 steps of deduction "
    "(NOT deep multi-step). Focus on: arithmetic with a single trap (sign error, wrong operation "
    "order, off-by-one), basic algebra, simple probability/combinatorics, conditional logic. "
    "A capable 7B model should answer about 65-72% correctly, because one distractor is the "
    "result of a GENUINE small mistake (one wrong step: sign flip, swapped operation, misread "
    "number) — never random or obviously-wrong numbers. Pure reasoning only — NOT factual "
    "knowledge, trivia, memorization, or domain breadth. No question solvable by recall alone. "
    "Exactly one correct option among A/B/C/D; keep it self-contained (Chinese or English)."
)

def build_prompt(n):
    return (
        f"Generate {n} MODERATELY HARD reasoning questions (pure reasoning, 1-2 steps, one "
        "plausible trap; no factual/trivia/knowledge breadth, no lookup-by-memory). Output ONLY "
        "a JSON array, no prose, each element:\n"
        '[{"q":"<question text>",'
        '"options":{"A":"<opt>","B":"<opt>","C":"<opt>","D":"<opt>"},'
        '"answer":"<A|B|C|D>","rationale":"<why correct, mention the key step>",'
        '"common_error":"<the single mistake that leads to the WRONG but plausible distractor>"}, ...]\n'
        "Rules: (1) every question needs 1-2 steps of reasoning with a SINGLE trap, never deep "
        "multi-step; (2) at least one distractor must be the RESULT of a real small error "
        "(arithmetic slip, sign flip, swapped operation, off-by-one) — that is the trap; "
        "(3) no question answerable from memory or general knowledge alone; "
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
    ap.add_argument("--live", default=str(LIVE_PATH),
                    help="实时看板 live 文件路径(生成阶段逐批写入, 让面板同步显示)")
    args = ap.parse_args()

    cfg = dict(DEFAULT_CFG)
    have = count_existing()
    print(f"[gen_midhard] pool={POOL_PATH} existing={have} target={args.target}", flush=True)
    if have >= args.target:
        print("[gen_midhard] 已达目标, 退出"); return

    try:
        V.warmup_models(cfg)
    except Exception as e:
        print("[gen_midhard] warmup warn:", e, flush=True)

    created = have
    attempts = 0
    write_live({"status": "running", "phase": "gen-midhard",
                "progress": f"生成中 {created}/{args.target}", "updated_at": time.strftime("%H:%M:%S")},
               args.live)
    while created < args.target and attempts < args.target * 3:
        attempts += 1
        remain = min(BATCH, args.target - created)
        try:
            txt = generate(build_prompt(remain), SYSTEM, cfg, model=args.creator, max_tokens=3072)
        except Exception as e:
            print("[gen_midhard] gen err:", e, flush=True); time.sleep(2); continue
        items = parse_batch(txt)
        if not items:
            print(f"[gen_midhard] batch parse empty (attempt {attempts})", flush=True); continue
        with open(POOL_PATH, "a", encoding="utf-8") as f:
            for it in items:
                f.write(json.dumps(it, ensure_ascii=False) + "\n")
        created += len(items)
        print(f"[gen_midhard] +{len(items)} -> pool={created}/{args.target}", flush=True)
        # 实时刷新看板(逐批), 让面板同步显示进度而非冻结在循环入口值
        write_live({"status": "running", "phase": "gen-midhard",
                    "progress": f"生成中 {created}/{args.target}", "updated_at": time.strftime("%H:%M:%S")},
                   args.live)
        time.sleep(0.3)

    print(f"[gen_midhard] DONE pool={count_existing()} path={POOL_PATH}", flush=True)

if __name__ == "__main__":
    main()
