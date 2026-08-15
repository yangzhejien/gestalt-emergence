#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
格式塔方程 Stage 2 —— 协作合成架构 (非投票)
============================================
架构(用户 2026-08-03 口述, canonical 顺序):
  L3 集群(底层, 3x qwen2.5:1.5b 专业 persona)
      │  各出候选答案+推理
      ▼
  聚合层(3b): 产出「聚合简报」(=Σsᵢ 加性基础) + 「分歧/残留」(双通道)
      │  聚合简报 + 未聚合残留  ──┐ 同时上送
      ▼                         │
  L2 副脑(3b): 判断/裁定
      ▼
  L1 主脑(7b): 综合成最终答案 = 集体答案
      ▲
  验证层(每个位置旁挂 1.5b 抽检)

方程对应: M = Σsᵢ + ΣαₘẆ²ᵐ
  Σsᵢ        = 聚合层「聚合简报」(基础能力之和, 加性/次线性)
  「分歧残留」 = 跨层连接密度 Ẇ 生成 ΣαₘẆ²ᵐ 非线性涌现增益的输入燃料
  conn_w     = 跨层连接强度 Ẇ 的操作化(0=只信聚合基础, 1=充分剥削残留/分歧)
  G(Ẇ)       = cap(集体) - cap(断连委员会0)  —— 连接协同增益, 应随 Ẇ 超线性增长

判据(同量纲):
  beats_best = 集体准确率 > 最强单模型准确率(本轮基准=7b=0.84)
  G_max      = max_Ẇ [cap(集体)-cap(委员会0)] > 0  => 仅说明集体比断连委员会票强, 不等于涌现
  ★ 涌现签名 = 峰值须落在 Ẇ>0 且相对 Ẇ=0 有正向梯度(ΣαẆ²ᵐ 随密度贡献额外增益);
    若峰值在 Ẇ=0 / 三档全平, 则集体仅≈加性平台, 不能判涌现(无论 beats_best 是否数值成立)

实时写 stage2_live.json(工作区, 沙箱允许), 供看板轮询。
"""
import json, urllib.request, math, re, csv, os, sys, argparse, random, time, ast
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(r"C:/Users/11409/WorkBuddy/2026-07-28-21-49-24/gestalt_live")
LIVE_PATH = OUT / "stage2_live.json"
SOLO_CACHE = OUT / "solo_checkpoint.json"

DEFAULT_CFG = {
    "l3_model": "qwen2.5:1.5b",
    "l3_personas": [
        "You are a mathematics and calculation expert. Solve carefully.",
        "You are a programming and formal-logic expert. Reason rigorously.",
        "You are a general-knowledge and fact-retrieval expert. Use broad knowledge.",
        "You are a physics and chemistry expert. Apply first principles.",
        "You are a biology and life-science expert. Reason from evidence.",
        "You are a history and social-science expert. Use contextual knowledge.",
        "You are a language and reading-comprehension expert. Parse carefully.",
    ],
    "agg_model": "qwen2.5:3b",
    "l2_model": "qwen2.5:3b",
    "l1_model": "qwen2.5:7b",
    "verifier_model": "qwen2.5:1.5b",
    "k": 3,
    "benchmark": "benchmark/mcq_medium_clean.jsonl",
    "n_questions": 500,
    "temperature": 0.0,
    "ollama_url": "http://127.0.0.1:11434/api/generate",
}


# ---------- Ollama 调用(复用 verify_head 的稳健写法) ----------
def _gen_options(cfg, max_tokens):
    """构造 Ollama options；若 cfg 含 seed 则透传 options.seed，使生成可复现。"""
    opts = {"temperature": cfg.get("temperature", 0.0), "num_predict": max_tokens}
    if cfg.get("seed") is not None:
        opts["seed"] = cfg["seed"]
    return opts


def generate(prompt, system, cfg, model=None, timeout=300, max_tokens=384):
    body = {
        "model": model if model else cfg["l3_model"],
        "prompt": prompt,
        "system": system,
        "stream": False,
        # 常驻模型, 避免档间/题间 Ollama 卸载-重载抖动(本机为 CPU 推理, 重载极慢). 每次保留 1h.
        "keep_alive": "1h",
        # num_predict 限制生成长度: MCQ 推理默认 384 足够; 生成类任务(如造题)须显式放大,
        # 否则输出被截断 -> JSON 不完整 -> 解析失败. 通过 max_tokens 参数透传.
        "options": _gen_options(cfg, max_tokens),
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        cfg["ollama_url"], data=data, headers={"Content-Type": "application/json"}
    )
    last = None
    for attempt in range(2):  # 2 次重试; 单次挂死最多 ~2*timeout, 避免长时间卡死
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8")).get("response", "")
        except Exception as e:
            last = e
            sys.stderr.write(f"[generate retry {attempt}] {e}\n"); sys.stderr.flush()
            time.sleep(min(2 ** attempt, 15))
    sys.stderr.write(f"[generate FAIL, blank] {last}\n"); sys.stderr.flush()
    return ""


def warmup_models(cfg):
    """启动前把全部模型预热并常驻(keep_alive=-1), 避免运行中卸载-重载抖动.
    本机 CPU 推理, 冷加载一个 7b 可达分钟级, 必须前置."""
    models = list(dict.fromkeys(
        [cfg["l3_model"], cfg["agg_model"], cfg["l2_model"],
         cfg.get("orchestrator_model", cfg["l1_model"]),
         cfg["verifier_model"]] + list(cfg.get("participant_models", []))))
    sys.stderr.write(f"[warmup] 预热 {len(models)} 个模型并常驻...\n"); sys.stderr.flush()
    for m in models:
        try:
            body = json.dumps({"model": m, "prompt": "ping", "stream": False,
                                "keep_alive": -1}).encode("utf-8")
            req = urllib.request.Request(cfg["ollama_url"], data=body,
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=300) as r:
                json.loads(r.read().decode("utf-8"))
            sys.stderr.write(f"[warmup] OK {m}\n"); sys.stderr.flush()
        except Exception as e:
            sys.stderr.write(f"[warmup] FAIL {m}: {e}\n"); sys.stderr.flush()


LETTER_RE = re.compile(r"(?:^|[^A-Za-z])([A-D])(?:[^A-Za-z]|$)")
FINAL_RE = re.compile(r"(?:最终答案|裁定答案|answer|final)\s*[:：]\s*\(?([A-D])", re.I)
def extract_choice(text):
    if not text:
        return None
    m = FINAL_RE.search(text)
    if m:
        return m.group(1)
    # 兜底: 取首个独立字母
    m = LETTER_RE.search(text)
    return m.group(1) if m else None


def majority_vote(answers, tiebreak=None):
    counts, order = {}, []
    for a in answers:
        if a is None:
            continue
        if a not in counts:
            counts[a] = 0; order.append(a)
        counts[a] += 1
    if not counts:
        return tiebreak
    best = max(counts.values())
    winners = [a for a in order if counts[a] == best]
    return winners[0] if len(winners) == 1 else (tiebreak if tiebreak is not None else winners[0])


def cap(p, clamp=1e-3):
    p = min(max(p, clamp), 1 - clamp)
    return math.log(p / (1 - p))


def fit(terms, rows):
    X = np.array([[r["What"] ** t for t in terms] for r in rows], dtype=float)
    y = np.array([r["G"] for r in rows], dtype=float)
    coeffs, res, rank, sv = np.linalg.lstsq(X, y, rcond=None)
    pred = X @ coeffs
    ss_res = float(np.sum((y - pred) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-12 else 1.0
    if rank < len(terms):
        r2 = float("nan")
    return coeffs.tolist(), r2


def save_live(state):
    state["updated_at"] = time.strftime("%H:%M:%S")
    try:
        tmp = LIVE_PATH.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        os.replace(tmp, LIVE_PATH)
    except Exception as e:
        sys.stderr.write(f"[save_live ERROR] {e}\n"); sys.stderr.flush()


# ---------- 提示词 ----------
def q_block(q):
    # 兼容两种基准 schema:
    #   中难度: {question, A, B, C, D}
    #   高难题库: {q, options, answer, rationale} (options 可能是 dict 或字符串 repr)
    if "question" in q:
        return (f"Question: {q['question']}\n"
                f"A. {q['A']}\nB. {q['B']}\nC. {q['C']}\nD. {q['D']}\n")
    opts = q.get("options")
    if isinstance(opts, str):
        try:
            opts = ast.literal_eval(opts)
        except Exception:
            opts = {}
    if not isinstance(opts, dict):
        opts = {}
    qtext = q.get("q", q.get("question", ""))
    return (f"Question: {qtext}\n"
            f"A. {opts.get('A')}\nB. {opts.get('B')}\nC. {opts.get('C')}\nD. {opts.get('D')}\n")

def build_l3(q, persona):
    return (q_block(q) +
            "Answer with your best single letter (A/B/C/D) and a one-sentence reason.\n"
            "Format:\nAnswer: <letter>\nReason: <one sentence>")

def build_agg(q, l3):
    s = q_block(q) + "Three junior experts answered:\n"
    for i, (role, resp) in enumerate(l3):
        s += f"- Expert{i+1} ({role}): {resp.strip()[:600]}\n"
    s += ("You are the AGGREGATION layer. Produce TWO parts:\n"
          "1) Aggregation Brief: synthesize the consensus / main tendency.\n"
          "2) Disagreements & Residual: list where experts disagree and any valuable point an individual raised that the consensus missed.\n"
          "Be concise. Headings: 'Aggregation Brief:' and 'Disagreements & Residual:'.")
    return s

def build_l2(q, brief, residual, conn_w):
    return (q_block(q) +
            f"Aggregation Brief:\n{brief.strip()}\n\n"
            f"Disagreements & Residual:\n{residual.strip()}\n\n"
            f"Cross-layer connection strength = {conn_w:.2f} "
            f"(0 = rely only on the aggregation base; 1 = fully exploit the residual/disagreements across layers).\n"
            "You are the DEPUTY brain (副脑). Make your own judgment on the final answer, weighing the residual strongly.\n"
            "Format:\nVerdict: <letter>\nReasoning: <one sentence>")

def build_l1(q, brief, residual, l2, conn_w):
    return (q_block(q) +
            f"Aggregation Brief:\n{brief.strip()}\n\n"
            f"Disagreements & Residual:\n{residual.strip()}\n\n"
            f"Deputy verdict: {l2.strip()}\n\n"
            f"Cross-layer connection strength = {conn_w:.2f} "
            f"(0 = rely only on the aggregation base; 1 = fully exploit the residual across layers).\n"
            "You are the CHIEF brain (主脑). Synthesize everything into the FINAL answer.\n"
            "Format:\nFinal Answer: <letter>\nReasoning: <one sentence>")

def build_verify(q, final):
    return (q_block(q) +
            f"Proposed final answer: {final}\n"
            "Is this answer valid (one of A/B/C/D) and not self-contradictory with the question? "
            "Reply with exactly one word: PASS or FAIL.")


# ---------- 主流程 ----------
def run_pipeline(q, cfg, conn_w, state):
    # L3 集群
    l3 = []
    personas = cfg["l3_personas"]
    for i in range(cfg["k"]):
        persona = personas[i % len(personas)]
        resp = generate(build_l3(q, persona), persona, cfg, model=cfg["l3_model"])
        l3.append((persona.split('.')[0], resp))
    # 参与者模型(消融 demote: 7b 降级进集群, 作为普通专家参与聚合, 不作主脑/不生成最终答案)
    for pm in cfg.get("participant_models", []):
        resp = generate(build_l3(q, "You are a careful senior expert. Solve carefully."),
                        "expert", cfg, model=pm)
        l3.append(("senior", resp))
    l3_choices = [extract_choice(r[1]) for r in l3]
    # 聚合层(双通道)
    # 聚合层必须放大生成上限: k>=5 时 k 个 L3 完整输出拼入, 3b 需生成「简报+残留」两部分,
    # 默认 384 token 不够 -> 截断在 'Disagreements & Residual' 之前 -> 主脑喂垃圾 -> 集体崩.
    # 实证: k=5 原跑 collective=0.478(崩), k=3 正常(0.945). 放大到 1024 修复.
    agg_resp = generate(build_agg(q, l3), "You are the aggregation layer.", cfg, model=cfg["agg_model"], max_tokens=1024)
    # 简单切分: 取 'Disagreements & Residual' 之后为残留, 之前为简报
    m = re.search(r"Disagreements\s*&\s*Residual\s*[:：](.*)", agg_resp, re.I | re.S)
    if m:
        brief = agg_resp[:m.start()].replace("Aggregation Brief:", "").replace("Aggregation Brief", "").strip()
        residual = m.group(1).strip()
    else:
        # 鲁棒 fallback: 即使生成被截断没出现 Residual 段, 也尽力保留 Aggregation Brief 部分
        mb = re.search(r"Aggregation\s+Brief\s*[:：](.*)", agg_resp, re.I | re.S)
        if mb:
            brief = mb.group(1).strip()
            residual = "(residual section missing in aggregation output; degraded mode)"
        else:
            brief, residual = agg_resp.strip(), "(none extracted)"
    # L2 副脑
    l2_resp = generate(build_l2(q, brief, residual, conn_w), "You are the deputy brain.", cfg, model=cfg["l2_model"])
    l2_choice = extract_choice(l2_resp)
    # 验证层(L2 旁挂, 轻量)
    v2 = generate(build_verify(q, l2_choice or "?"), "You are a verifier.", cfg, model=cfg["verifier_model"])
    l2_ok = ("PASS" in (v2 or "").upper())
    # L1 主脑
    l1_resp = generate(build_l1(q, brief, residual, l2_resp, conn_w), "You are the chief brain.", cfg, model=cfg["orchestrator_model"])
    l1_choice = extract_choice(l1_resp)
    # 验证层(L1 旁挂, 失败重试1次)
    v1 = generate(build_verify(q, l1_choice or "?"), "You are a verifier.", cfg, model=cfg["verifier_model"])
    if "FAIL" in (v1 or "").upper() and l1_choice:
        l1_resp = generate(build_l1(q, brief, residual, l2_resp, conn_w) + "\n(The previous answer failed verification. Re-check and give a confident final.)",
                           "You are the chief brain.", cfg, model=cfg["orchestrator_model"])
        l1_choice = extract_choice(l1_resp)
        v1 = generate(build_verify(q, l1_choice or "?"), "You are a verifier.", cfg, model=cfg["verifier_model"])
    l1_ok = ("PASS" in (v1 or "").upper())
    return {
        "l3_choices": l3_choices, "l2_choice": l2_choice, "l1_choice": l1_choice,
        "l2_verified": l2_ok, "l1_verified": l1_ok,
        "brief": brief[:200], "residual": residual[:200],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--n", type=int, default=None)
    ap.add_argument("--conn-w", default="1.0", help="逗号分隔的跨层连接强度(Ẇ)档, 默认 1.0")
    ap.add_argument("--live", default="stage2_live.json")
    ap.add_argument("--temperature", type=float, default=None, help="覆盖采样温度(默认用cfg); >0 引入随机性用于复现分布")
    ap.add_argument("--seed", type=int, default=None, help="固定随机种子: 同时 seed Python random 并透传 Ollama(options.seed) 使生成可复现; 默认不设(沿用 temp=0 近确定性)")
    ap.add_argument("--k", type=int, default=None,
                    help="L3 独立专家数(k); 默认用cfg。增大k对应提高连接密度W(Condorcet征募更多独立专家), 用于扫描Wc峰位")
    ap.add_argument("--benchmark", default=None, help="覆盖题库路径(相对ROOT或绝对), 默认用cfg['benchmark']")
    ap.add_argument("--ablation", choices=["none", "demote", "remove"], default="none",
                    help="消融模式: none=默认(7b主脑); demote=7b降级为参与者(进L3集群)+新3b主脑; remove=彻底移除7b,3b主脑")
    ap.add_argument("--no-live", action="store_true")
    ap.add_argument("--out", default=None,
                    help="输出目录(存放 live json / tiers / 验证报告)。默认=作者机器绝对路径, 跨机无效;"
                          "请务必用 --out 指定自己机器目录。通过 run_experiments.sh 启动时已自动设置 --out, 无需手动指定")
    args = ap.parse_args()

    global OUT, LIVE_PATH, SOLO_CACHE
    if args.out:
        OUT = Path(args.out).resolve()
    OUT.mkdir(parents=True, exist_ok=True)
    LIVE_PATH = OUT / args.live
    SOLO_CACHE = OUT / "solo_checkpoint.json"

    cfg = dict(DEFAULT_CFG)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    if args.benchmark:
        cfg["benchmark"] = args.benchmark
    if args.temperature is not None:
        cfg["temperature"] = args.temperature
        print(f"[info] 采样温度覆盖为 {cfg['temperature']}")
    if args.seed is not None:
        cfg["seed"] = args.seed
        random.seed(args.seed)
        print(f"[info] 随机种子固定为 {cfg['seed']}")
    if args.k is not None:
        cfg["k"] = args.k
        print(f"[info] L3 独立专家数 k 覆盖为 {cfg['k']}")

    # ----- 消融模式: 配置主脑(编排者)与参与者 -----
    # 默认: 7b 任主脑(编排者/最终答案生成者), 无额外参与者
    cfg["orchestrator_model"] = cfg["l1_model"]
    cfg["participant_models"] = []
    if args.ablation == "demote":
        # 7b 降级为 L3 集群中的参与者(强模型但非编排者), 新 3b 任主脑
        cfg["orchestrator_model"] = "qwen2.5:3b"
        cfg["participant_models"] = [cfg["l1_model"]]
        print(f"[ablation=demote] 主脑={cfg['orchestrator_model']} 参与者(含7b)={cfg['participant_models']}")
    elif args.ablation == "remove":
        # 彻底移除 7b, 3b 任主脑; 弱群(1.5b集群+3b编排) vs 7b solo
        cfg["orchestrator_model"] = "qwen2.5:3b"
        cfg["participant_models"] = []
        print(f"[ablation=remove] 主脑={cfg['orchestrator_model']} 7b 已移除")

    # 预热: CPU 推理下必须前置, 避免运行中模型卸载-重载抖动导致超时卡死
    warmup_models(cfg)

    conn_levels = [float(x) for x in args.conn_w.split(",")]
    bench_path = ROOT / cfg["benchmark"]
    questions = []
    with open(bench_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                questions.append(json.loads(line))
    if args.n:
        questions = questions[:args.n]
    for i, q in enumerate(questions):
        q.setdefault("id", f"q{i+1}")
    print(f"[info] l3={cfg['l3_model']} agg/l2={cfg['agg_model']} l1={cfg['l1_model']} n={len(questions)} conn_w={conn_levels}")

    sig = f"{str(bench_path)}|n={len(questions)}|k={cfg['k']}"
    state = {
        "status": "running", "phase": "solo",         "models": {
            "l3": cfg["l3_model"], "agg": cfg["agg_model"], "l2": cfg["l2_model"],
            "orchestrator": cfg["orchestrator_model"], "l1_original": cfg["l1_model"],
            "participants": cfg.get("participant_models", []),
            "verifier": cfg["verifier_model"]},
        "n_questions": len(questions), "conn_levels": conn_levels,
        "progress": "", "node_acc": {}, "best_single": None,
        "committee0": None, "collective_acc": {}, "points": [],
        "details": [], "judgement": "", "benchmark_sig": sig,
    }
    if not args.no_live:
        save_live(state)

    # ----- 阶段A: 单模型基线(公平对照), 题级断点续跑(抗休眠/回收) -----
    # 关键修复: 原版 solo 仅在「全部算完才写一次 SOLO_CACHE」, 中途崩溃(如笔记本休眠带停
    # ollama) 会整段 solo 全丢、从 0 重算(已致 k20 白跑数小时)。现改为题级增量写入:
    # 每算完一题 append 一行到按 live-stem 隔离的 jsonl, 重启时仅补算未完成题。
    solo_keys = [f"l3_{i}" for i in range(cfg["k"])] + ["l2_3b", "l1_7b"]
    solos = {}  # model_key -> [choices]
    node_acc_list = []
    best_single = None
    acc0 = None
    cache_ok = False

    solo_stem = LIVE_PATH.stem  # 例如 stage2_density_k20 —— 隔离不同 k 的增量断点
    SOLO_JSONL = OUT / f"solo_{solo_stem}_checkpoint.jsonl"
    completed = {}  # (model_key, q_idx) -> choice
    if SOLO_JSONL.exists():
        try:
            for _ln in SOLO_JSONL.read_text(encoding="utf-8").splitlines():
                _ln = _ln.strip()
                if _ln:
                    _r = json.loads(_ln)
                    completed[(_r["mk"], _r["qi"])] = _r["c"]
            print(f"[solo] 载入增量断点 {len(completed)} 条")
        except Exception as e:
            print(f"[solo] 增量断点读取失败, 从头: {e}")
            completed = {}

    if not getattr(args, "force_solo", False) and SOLO_CACHE.exists():
        try:
            c = json.loads(SOLO_CACHE.read_text(encoding="utf-8"))
            if (c.get("benchmark") == str(args.benchmark) and c.get("k") == cfg["k"]
                    and c.get("n") == len(questions)
                    and len(c.get("solos", {})) == len(solo_keys)):
                solos = c["solos"]; node_acc_list = c["node_acc_list"]
                best_single = c["best_single"]; acc0 = c["committee0"]
                cache_ok = True
                print("[solo] 命中断点缓存, 跳过基线重算")
        except Exception as e:
            print(f"[solo] 缓存读取失败, 重新计算: {e}")

    if not cache_ok:
        personas = cfg["l3_personas"]
        # 预分配结构并从增量断点恢复已完成题
        for mk in solo_keys:
            solos[mk] = [None] * len(questions)
        for mk in solo_keys:
            _done = sum(1 for (k, qi) in completed if k == mk)
            if _done == len(questions):
                # 该模型全部完成 -> 直接恢复, 跳过
                for qi in range(len(questions)):
                    solos[mk][qi] = completed[(mk, qi)]
                _acc = sum(1 for a, q in zip(solos[mk], questions) if a == q["answer"]) / len(questions)
                node_acc_list.append(round(_acc, 4))
                print(f"  {mk} solo 增量恢复 acc={_acc:.3f} (skip)")
                continue
            # 该模型需补算/初算
            if mk.startswith("l3_"):
                _i = int(mk.split("_")[-1]); _model = cfg["l3_model"]; _persona = personas[_i % len(personas)]
            elif mk == "l2_3b":
                _model = cfg["agg_model"]; _persona = "You are a careful general expert."
            else:  # l1_7b
                _model = cfg["l1_model"]; _persona = "You are a careful general expert."
            for ti, q in enumerate(questions):
                if (mk, ti) in completed:
                    solos[mk][ti] = completed[(mk, ti)]
                    continue
                _choice = extract_choice(generate(build_l3(q, _persona), _persona, cfg, model=_model))
                solos[mk][ti] = _choice
                completed[(mk, ti)] = _choice
                try:
                    with open(SOLO_JSONL, "a", encoding="utf-8") as _f:
                        _f.write(json.dumps({"mk": mk, "qi": ti, "c": _choice}, ensure_ascii=False) + "\n")
                        _f.flush()
                except Exception as _we:
                    print(f"[solo] 增量写失败(非致命): {_we}")
                state["progress"] = f"Solo {mk}  q {ti+1}/{len(questions)}"
                if not args.no_live: save_live(state)
            _acc = sum(1 for a, q in zip(solos[mk], questions) if a == q["answer"]) / len(questions)
            node_acc_list.append(round(_acc, 4))
            print(f"  {mk} solo acc={_acc:.3f}")
        # 写全量断点缓存(全部 solo 完成), 供后续快速命中 + 跨 run 复用
        try:
            _c0 = [majority_vote([solos[f"l3_{i}"][ti] for i in range(cfg["k"])], tiebreak=solos["l3_0"][ti]) for ti in range(len(questions))]
            _acc0c = sum(1 for a, q in zip(_c0, questions) if a == q["answer"]) / len(questions)
            SOLO_CACHE.write_text(json.dumps({
                "benchmark": str(args.benchmark), "k": cfg["k"], "n": len(questions),
                "solos": solos, "node_acc_list": node_acc_list,
                "best_single": max(node_acc_list), "committee0": _acc0c,
            }, ensure_ascii=False), encoding="utf-8")
            print("[solo] 断点缓存已写")
        except Exception as e:
            print(f"[solo] 缓存写入失败(非致命): {e}")

    state["node_acc"] = node_acc_list
    _ab = args.ablation if hasattr(args, "ablation") else "none"
    state["node_model"] = (f"{cfg['l3_model']}x{cfg['k']} + {cfg['agg_model']}(agg/L2) "
                           f"+ {cfg['orchestrator_model']}(主脑) + 参与者{cfg.get('participant_models', [])} "
                           f"[ablation={_ab}]")
    if best_single is None:
        best_single = max(node_acc_list)
    state["best_single"] = round(best_single, 4)
    if acc0 is None:
        try:
            committee0 = [majority_vote([solos[f"l3_{i}"][ti] for i in range(cfg["k"])], tiebreak=solos["l3_0"][ti])
                          for ti in range(len(questions))]
            acc0 = sum(1 for a, q in zip(committee0, questions) if a == q["answer"]) / len(questions)
        except Exception as e:
            print(f"[baseline] committee0 计算失败(非致命, fallback=best_single): {e}")
            acc0 = best_single
            committee0 = [solos["l3_0"][ti] for ti in range(len(questions))]
    state["committee0"] = round(acc0, 4)
    state["A_net0"] = round(acc0, 4)
    print(f"[baseline] best_single={best_single:.3f} committee0(L3 vote)={acc0:.3f}")
    if not args.no_live: save_live(state)

    # ----- 阶段B: 协作合成管线(扫 conn_w), 题级断点续跑(抗环境回收) -----
    qid2idx = {q["id"]: i for i, q in enumerate(questions)}
    TIER_DIR = OUT / "tiers"
    TIER_DIR.mkdir(parents=True, exist_ok=True)
    live_stem = LIVE_PATH.stem  # 用 live 文件名隔离不同复现的题级文件
    rows = []
    for cw in conn_levels:
        key = f"cw{cw:.2f}"
        tier_file = TIER_DIR / f"{live_stem}_cw{cw:.2f}.jsonl"
        # 载入已完成题(题级断点)
        completed = {}
        if tier_file.exists():
            try:
                with open(tier_file, encoding="utf-8") as tf:
                    for line in tf:
                        line = line.strip()
                        if line:
                            d = json.loads(line)
                            completed[d["q"]] = d
            except Exception as e:
                print(f"[tier {key}] 读取断点失败, 整档重跑: {e}")
                completed = {}
        coll_choices = [None] * len(questions)
        for d in completed.values():
            idx = qid2idx.get(d["q"])
            if idx is not None:
                coll_choices[idx] = d.get("l1_choice")
        state["phase"] = f"pipeline Ẇ={cw:.2f}"; state["current_w"] = cw
        if len(completed) >= len(questions):
            # 整档已完成 -> 直接由断点重建, 不重跑
            acc_coll = sum(1 for a, q in zip(coll_choices, questions) if a == q["answer"]) / len(questions)
            state["collective_acc"][key] = round(acc_coll, 4)
            rows.append({"w": cw, "What": cw, "A_net0": acc0, "A_net_w": acc_coll,
                         "G": cap(acc_coll) - cap(acc0), "conn_w": cw, "committee0": acc0, "collective": acc_coll})
            state["details"] = [completed[q["id"]] for q in questions if q["id"] in completed]
            save_live(state)
            print(f"  Ẇ={cw:.2f} TIER DONE(resumed) collective={acc_coll:.3f}")
            continue
        none_cnt = 0
        with open(tier_file, "a", encoding="utf-8") as tf:
            for ti, q in enumerate(questions):
                if q["id"] in completed:
                    continue
                r = run_pipeline(q, cfg, cw, state)
                coll_choices[ti] = r["l1_choice"]
                rec = {"q": q["id"], "l3": r["l3_choices"], "l2": r["l2_choice"],
                       "l1": r["l1_choice"], "l1_ok": r["l1_verified"]}
                tf.write(json.dumps(rec, ensure_ascii=False) + "\n"); tf.flush()
                completed[q["id"]] = rec
                if r["l1_choice"] is None:
                    none_cnt += 1
                state["progress"] = f"Pipeline Ẇ={cw:.2f}  q {ti+1}/{len(questions)} (done {len(completed)})"
                done_n = sum(1 for a in coll_choices if a is not None)
                if done_n:
                    acc_inc = sum(1 for a, qq in zip(coll_choices, questions) if a == qq["answer"] and a is not None) / done_n
                    state["collective_acc"][key] = round(acc_inc, 4)
                save_live(state)
        if none_cnt > len(questions) * 0.5:
            print(f"[WARN] Ẇ={cw:.2f} 超过半数题主脑返回空(可能 Ollama 异常), 结果存疑")
            state.setdefault("warnings", []).append(f"cw{cw:.2f}: {none_cnt}/{len(questions)} 空响应")
        acc_coll = sum(1 for a, q in zip(coll_choices, questions) if a == q["answer"]) / len(questions)
        rows.append({"w": cw, "What": cw, "A_net0": acc0, "A_net_w": acc_coll,
                     "G": cap(acc_coll) - cap(acc0), "conn_w": cw, "committee0": acc0, "collective": acc_coll})
        state["collective_acc"][key] = round(acc_coll, 4)
        state["details"] = [completed[q["id"]] for q in questions if q["id"] in completed]
        print(f"  Ẇ={cw:.2f} collective={acc_coll:.3f} G={cap(acc_coll)-cap(acc0):+.3f}")
        save_live(state)

    # ----- 拟合 G ~ α1 Ẇ² + α2 Ẇ⁴ -----
    fit_obj = None
    if len(rows) >= 2:
        c, r2 = fit([2, 4], rows)
        cl, r2l = fit([1], rows)
        fit_obj = {"alpha1": round(c[0], 4), "alpha2": round(c[1], 4),
                   "r2": (round(r2, 4) if not math.isnan(r2) else None),
                   "r2_lin": round(r2l, 4)}
        if math.isnan(r2):
            fit_obj["note"] = "需≥3个Ẇ档才能区分α1/α2"
    state["points"] = rows
    state["fit"] = fit_obj

    # 防御性收尾: 直接从已落盘的 collective_acc 反算, 避免 rows 内部结构异常导致 AttributeError
    _coll_vals = [(cw, state["collective_acc"][f"cw{cw:.2f}"])
                  for cw in conn_levels if f"cw{cw:.2f}" in state["collective_acc"]]
    collective_max = max((v for _, v in _coll_vals), default=0.0)
    opt_cw = next((cw for cw, v in _coll_vals if v == collective_max), 0.0)
    G_max = max(((v - acc0) for _, v in _coll_vals), default=0.0)
    beats_best = collective_max > best_single
    state["superlinear"] = {
        "best_single": round(best_single, 4), "committee0": round(acc0, 4),
        "collective_max": round(collective_max, 4), "opt_conn_w": opt_cw,
        "G_max": round(G_max, 4), "beats_best": beats_best,
    }
    # 涌现判据: 非线性项须在 Ẇ>0 处产生额外增益(峰值不在Ẇ=0 且相对Ẇ=0有正向梯度)
    coll_w0 = next((v for cw, v in _coll_vals if cw == 0.0), None)
    gain_from_w0 = (collective_max - coll_w0) if (coll_w0 is not None) else 0.0
    emergence = (opt_cw > 0) and (gain_from_w0 > 0.02)  # 2pt 阈值, 防噪声误判
    if beats_best and emergence:
        verdict = "beats_best 成立且峰值在Ẇ>0(非线性项贡献) => 涌现协同初步证据"
    elif beats_best and not emergence:
        verdict = ("beats_best 数值成立但峰值在Ẇ=0(三档全平/加性平台), "
                   "非线性项未贡献, 不能判涌现")
    else:
        verdict = "未超过最强单模型, 无涌现"
    judge = (f"协作合成(非投票): 集体最优(Ẇ={opt_cw:.2f})={collective_max:.3f} vs 最强单模型={best_single:.3f}. "
             f"{verdict}. "
             f"G_max={G_max:+.3f} 为集体-委员会0固定基线差(恒定时不代表随Ẇ增强的涌现增益).")
    state["judgement"] = judge
    state["status"] = "done"; state["phase"] = "fit"
    if not args.no_live: save_live(state)

    # ----- 落盘报告 -----
    rep = OUT / f"verify_report_{LIVE_PATH.stem}.md"
    with open(rep, "w", encoding="utf-8") as f:
        f.write("# 格式塔方程 Stage 2 协作合成验证报告\n\n")
        f.write(f"- L3集群: {cfg['l3_model']} x{cfg['k']} (专业persona)\n")
        f.write(f"- 聚合层/副脑(L2): {cfg['agg_model']}\n- 主脑(编排者): {cfg['orchestrator_model']} (消融模式={args.ablation})\n- 原始L1/7b: {cfg['l1_model']} 参与者={cfg.get('participant_models', [])}\n- 验证层: {cfg['verifier_model']} 每位置旁挂\n")
        f.write(f"- 题数: {len(questions)}  跨层连接强度档 Ẇ={conn_levels}\n\n")
        f.write("## 单模型基线(公平对照)\n")
        _labels = ["l3_0", "l3_1", "l3_2", "l2_3b", "l1_7b"]
        for i, vv in enumerate(state["node_acc"]):
            _lab = _labels[i] if i < len(_labels) else f"node{i}"
            f.write(f"- {_lab}: {vv:.3f}\n")
        f.write(f"- 最强单模型: {best_single:.3f}\n- 断连委员会0(L3多数投票): {acc0:.3f}\n\n")
        f.write("## 协作合成结果\n| Ẇ(conn_w) | 委员会0 | 集体(主脑综合) | G |\n")
        for r in rows:
            f.write(f"| {r['conn_w']:.2f} | {r['committee0']:.3f} | {r['collective']:.3f} | {r['G']:+.3f} |\n")
        if fit_obj:
            f.write(f"\n## 拟合 G ~ α1Ẇ²+α2Ẇ⁴\n- α1={fit_obj['alpha1']} α2={fit_obj['alpha2']} R2={fit_obj['r2']} (线性R2={fit_obj['r2_lin']})\n")
        f.write(f"\n## 判定\n{judge}\n")
    print(f"\n[done] report -> {rep}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback as _tb
        _msg = _tb.format_exc()
        sys.stderr.write("[FATAL] " + _msg); sys.stderr.flush()
        try:
            _st = {}
            if LIVE_PATH.exists():
                try: _st = json.loads(LIVE_PATH.read_text(encoding="utf-8"))
                except Exception: pass
            _st["status"] = "error"; _st["error"] = _msg; _st["updated_at"] = time.strftime("%H:%M:%S")
            _tmp = LIVE_PATH.with_suffix(".tmp")
            with open(_tmp, "w", encoding="utf-8") as _f:
                json.dump(_st, _f, ensure_ascii=False, indent=2)
            os.replace(_tmp, LIVE_PATH)
        except Exception as _ee:
            sys.stderr.write(f"[FATAL write failed] {_ee}\n"); sys.stderr.flush()
        raise
