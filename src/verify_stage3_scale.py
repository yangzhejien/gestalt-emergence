#!/usr/bin/env python3
# verify_stage3_scale.py — 格式塔方程 扩节点验证 (多 L2 副脑分层)
# ─────────────────────────────────────────────────────────────────
# 架构 (按方程文档 5.1 三层 + 用户规则: 每 3 个 L3 节点配 1 个 L2 副脑):
#   N_l3 个 1.5B 专家 → 按 group_size(默认3) 划分为 ceil(N_l3/3) 个 L2 副脑(3B) 子组
#   每组内: L3×k -> 聚合层(3B, 双通道简报+残留) -> L2 deputy(3b) 产出"组裁定"
#   各 L2 组裁定 -> 顶层 L1 主脑(7b) 综合 -> 最终答案 (验证层旁挂)
# 复用 verify_stage2 的 generate / build_* / extract_choice, 不改 3 节点基线.
# 用途: 扩节点提 Ẇ 过 Wc, 实测 ΣαₘẆ²ᵐ 超线性涌现 (方程后半登场).
# ─────────────────────────────────────────────────────────────────
import sys, os, json, re, time, math, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify_stage2 as V

generate        = V.generate
extract_choice  = V.extract_choice
build_l3        = V.build_l3
build_agg       = V.build_agg
build_l2        = V.build_l2
build_l1        = V.build_l1
build_verify    = V.build_verify
warmup_models   = V.warmup_models
q_block         = V.q_block
DEFAULT_CFG     = V.DEFAULT_CFG

GESTALT_LIVE = V.OUT  # 与 stage2 同目录 gestalt_live/

# 20 个细分领域专家 persona (匹配文档"各自负责一个细分领域")
PERSONAS = [
    "You are a mathematics and arithmetic expert. Solve carefully.",
    "You are an algebra and equation-solving expert. Reason step by step.",
    "You are a geometry and spatial-reasoning expert. Be precise.",
    "You are a probability and statistics expert. Compute carefully.",
    "You are a combinatorics and discrete-math expert. Enumerate rigorously.",
    "You are a number-theory expert. Check divisibility and primes.",
    "You are a calculus and rate-of-change expert. Reason carefully.",
    "You are a physics expert. Apply formulas correctly.",
    "You are a chemistry expert. Balance and compute carefully.",
    "You are a biology and life-science expert. Reason from first principles.",
    "You are a formal-logic expert. Deduce rigorously.",
    "You are a programming and algorithms expert. Trace execution precisely.",
    "You are a general-knowledge and fact expert. Use broad knowledge.",
    "You are a history and chronology expert. Reason from context.",
    "You are a geography and map-reasoning expert. Be precise.",
    "You are an economics and finance expert. Compute carefully.",
    "You are a law and regulation expert. Apply rules strictly.",
    "You are a reading-comprehension expert. Infer precisely.",
    "You are a common-sense reasoning expert. Think practically.",
    "You are a data-analysis expert. Read tables and trends carefully.",
]

def persona_at(i):
    if i < len(PERSONAS):
        return PERSONAS[i]
    return f"You are domain specialist #{i+1}. Solve the problem carefully and commit to one final letter."

# ---------- 扩节点主流程 ----------
def run_scaled_pipeline(q, cfg, conn_w, n_l3, group_size):
    idxs_all = list(range(n_l3))
    groups = [idxs_all[i:i+group_size] for i in range(0, n_l3, group_size)]
    group_verdicts, group_briefs, group_residuals, l3_choices = [], [], [], []
    for gi, idxs in enumerate(groups):
        # L3 集群 (本组)
        l3 = []
        for j in idxs:
            persona = persona_at(j)
            resp = generate(build_l3(q, persona), persona, cfg, model=cfg["l3_model"])
            l3.append((persona.split('.')[0], resp))
        l3_choices.extend(extract_choice(r[1]) for r in l3)
        # 聚合层 (双通道)
        agg_resp = generate(build_agg(q, l3), "You are the aggregation layer.", cfg, model=cfg["agg_model"])
        m = re.search(r"Disagreements\s*&\s*Residual\s*[:：](.*)", agg_resp, re.I | re.S)
        if m:
            brief = agg_resp[:m.start()].replace("Aggregation Brief", "").strip()
            residual = m.group(1).strip()
        else:
            brief, residual = agg_resp.strip(), "(none extracted)"
        # L2 副脑 (本组裁定)
        l2_resp = generate(build_l2(q, brief, residual, conn_w), "You are the deputy brain.", cfg, model=cfg["l2_model"])
        l2_choice = extract_choice(l2_resp)
        v2 = generate(build_verify(q, l2_choice or "?"), "You are a verifier.", cfg, model=cfg["verifier_model"])
        l2_ok = ("PASS" in (v2 or "").upper())
        group_verdicts.append(l2_resp.strip())
        group_briefs.append(brief)
        group_residuals.append(residual)
    # 顶层 L1 主脑: 汇总全部组裁定 -> 最终答案
    combined_brief = "\n\n".join(f"[Group {i+1} aggregation brief]\n{b}" for i, b in enumerate(group_briefs))
    combined_resid = "\n\n".join(f"[Group {i+1} residual]\n{r}" for i, r in enumerate(group_residuals))
    group_text     = "\n\n".join(f"[Group {i+1} deputy verdict]\n{v}" for i, v in enumerate(group_verdicts))
    l1_resp = generate(build_l1(q, combined_brief, combined_resid, group_text, conn_w),
                       "You are the chief brain.", cfg, model=cfg["orchestrator_model"])
    l1_choice = extract_choice(l1_resp)
    v1 = generate(build_verify(q, l1_choice or "?"), "You are a verifier.", cfg, model=cfg["verifier_model"])
    if ("FAIL" in (v1 or "").upper()) and l1_choice:
        l1_resp = generate(build_l1(q, combined_brief, combined_resid, group_text, conn_w) +
                           "\n(The previous answer failed verification. Re-check and give a confident final.)",
                           "You are the chief brain.", cfg, model=cfg["orchestrator_model"])
        l1_choice = extract_choice(l1_resp)
        v1 = generate(build_verify(q, l1_choice or "?"), "You are a verifier.", cfg, model=cfg["verifier_model"])
    l1_ok = ("PASS" in (v1 or "").upper())
    return {"l3_choices": l3_choices, "group_verdicts": group_verdicts,
            "l1_choice": l1_choice, "l1_ok": l1_ok, "n_groups": len(groups)}

def run_solo(q, cfg, model):
    sys_p = "You are a careful expert. Solve the problem and commit to one final letter."
    resp = generate(q_block(q) +
                    "\nAnswer with your best single letter (A/B/C/D) and a one-sentence reason.\n"
                    "Format:\nAnswer: <letter>\nReason: <one sentence>",
                    sys_p, cfg, model=model)
    return extract_choice(resp)

def load_questions(path, n):
    qs = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
    return qs[:n]

def write_live(path, d):
    try:
        json.dump(d, open(path, "w", encoding="utf-8"), ensure_ascii=False)
    except Exception as e:
        sys.stderr.write(f"[live write fail] {e}\n")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--benchmark", default="benchmark/mcq_medium_clean.jsonl")
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--n-l3", type=int, default=20, help="L3 专家节点数 (1.5b)")
    ap.add_argument("--group-size", type=int, default=3, help="每几个 L3 配 1 个 L2 副脑")
    ap.add_argument("--conn-w", type=float, default=1.0)
    ap.add_argument("--live", default=str(GESTALT_LIVE / "stage3_scale_live.json"))
    ap.add_argument("--ablation", default="none",
                    help="none=7b主脑; demote=3b主脑+7b降级进L3集群; remove=无7b,3b主脑")
    ap.add_argument("--no-solo", action="store_true", help="跳过 7b solo 基线")
    args = ap.parse_args()

    cfg = dict(DEFAULT_CFG)
    cfg["k"] = args.n_l3
    # ablation
    if args.ablation == "demote":
        cfg["orchestrator_model"] = "qwen2.5:3b"
        cfg["participant_models"] = ["qwen2.5:7b"]   # 7b 降级进 L3 集群当普通专家
    elif args.ablation == "remove":
        cfg["orchestrator_model"] = "qwen2.5:3b"
        cfg["participant_models"] = []
    else:
        cfg["orchestrator_model"] = cfg["l1_model"]
        cfg["participant_models"] = []

    print(f"[stage3] n_l3={args.n_l3} group_size={args.group_size} "
          f"-> L2副脑数={math.ceil(args.n_l3/args.group_size)} 主脑={cfg['orchestrator_model']} "
          f"消融={args.ablation} n={args.n} conn_w={args.conn_w}", flush=True)

    warmup_models(cfg)
    questions = load_questions(args.benchmark, args.n)
    if not questions:
        print("[stage3] 无题目, 退出"); return

    live = {"phase": "init", "progress": "", "status": "running",
            "node_model": f"scale n_l3={args.n_l3} gs={args.group_size}",
            "n_l3": args.n_l3, "group_size": args.group_size,
            "n_groups": math.ceil(args.n_l3 / args.group_size),
            "collective_acc": {"cw1.00": None}, "node_acc": {}, "samples": []}
    write_live(args.live, live)

    # ---- 7b solo 基线 (best single, 公平对比同 n 题) ----
    best_single = None
    if not args.no_solo:
        live["phase"] = f"solo 7b (best_single)"
        write_live(args.live, live)
        correct = 0
        for i, q in enumerate(questions):
            c = run_solo(q, cfg, cfg["l1_model"])
            if c == q.get("answer"):
                correct += 1
            if (i + 1) % 10 == 0:
                sys.stderr.write(f"[solo] {i+1}/{len(questions)} acc={correct/(i+1):.3f}\n"); sys.stderr.flush()
        best_single = correct / len(questions)
        live["node_acc"] = {"best_single_7b": best_single}
        print(f"[stage3] 7b solo best_single = {best_single:.4f}", flush=True)

    # ---- 集体 (扩节点) ----
    live["phase"] = "collective (scaled)"
    write_live(args.live, live)
    correct = 0
    samples = []
    t0 = time.time()
    for i, q in enumerate(questions):
        try:
            r = run_scaled_pipeline(q, cfg, args.conn_w, args.n_l3, args.group_size)
            l1 = r["l1_choice"]
        except Exception as e:
            sys.stderr.write(f"[q{i}] pipeline error: {e}\n"); sys.stderr.flush()
            l1 = None
        ok = (l1 == q.get("answer"))
        if ok:
            correct += 1
        samples.append({"q": i, "l1": l1, "gold": q.get("answer"), "ok": ok,
                        "ng": r.get("n_groups")})
        acc = correct / (i + 1)
        live["collective_acc"] = {"cw1.00": acc}
        live["progress"] = f"collective q {i+1}/{len(questions)}"
        if (i + 1) % 1 == 0:
            write_live(args.live, live)
        if (i + 1) % 10 == 0:
            el = time.time() - t0
            sys.stderr.write(f"[collective] {i+1}/{len(questions)} acc={acc:.3f} "
                             f"elapsed={el/60:.1f}min\n"); sys.stderr.flush()

    acc = correct / len(questions)
    live["collective_acc"] = {"cw1.00": acc}
    live["phase"] = "done"
    live["status"] = "done"
    live["samples"] = samples
    live["node_acc"] = {"best_single_7b": best_single} if best_single is not None else live.get("node_acc", {})
    live["summary"] = {
        "collective": acc,
        "best_single_7b": best_single,
        "delta_vs_7b": (acc - best_single) if best_single is not None else None,
        "n_l3": args.n_l3, "n_groups": math.ceil(args.n_l3 / args.group_size),
    }
    write_live(args.live, live)
    print(f"[stage3 DONE] collective={acc:.4f} best_single_7b={best_single} "
          f"delta={acc-best_single if best_single is not None else float('nan'):+.4f}", flush=True)

if __name__ == "__main__":
    main()
