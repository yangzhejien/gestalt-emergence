#!/usr/bin/env python3
# verify_stage4_topology.py — 格式塔方程 拓扑密度(Ẇ)对照验证
# ─────────────────────────────────────────────────────────────────
# 目的: 在"同节点数、同基准"下, 仅改拓扑结构, 隔离 Ẇ(跨层连接密度)对集体准确率的
#       影响, 检验方程 M = Σsᵢ + ΣαₘẆ²ᵐ 后半(超线性涌现)是否随拓扑密度登场。
#
# 三种拓扑(控制变量):
#   tree  (复刻 stage3 树状): L3×k -> 聚合(双通道) -> L2副脑(每组1个) -> L1主脑
#          横向跨组连接 = 0; 跨层跳数 = 1。Ẇ 仅来自树状竖边(文档 5.1 的稀疏退化版)。
#   mesh  (扩拓扑/密): 在 tree 之上加:
#          (a) L2 横向全连网格: 每个副脑看到全部其他组的简报+裁定, 精炼(文档 5.1"副导之间协同连接")
#          (b) 主脑多跳: L1 初步 -> 回灌副脑二次精炼 -> L1 终裁; 跨层乘法深度 1->2
#   full  (文档最完整): mesh + L3 集群内部全连接(文档 5.1"集群内部全连接")
#          -> 同组专家互看首轮答案再精炼, 抬 L3 层 αₘ
#   机制(文档 2.1): αₘ 由拓扑决定, 全连接取最大值/稀疏减小; 故拓扑↑ -> αₘ↑ -> ΣαₘẆ²ᵐ↑。
#
# 复用 verify_stage2 的 generate/build_*/extract_choice/majority_vote;
# 复用 verify_stage3_scale 的 20 细分 persona (persona_at)。
# ─────────────────────────────────────────────────────────────────
import sys, os, json, re, time, math, argparse
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify_stage2 as V
from verify_stage3_scale import persona_at

generate        = V.generate
extract_choice  = V.extract_choice
build_l3        = V.build_l3
build_agg       = V.build_agg
build_l2        = V.build_l2
build_l1        = V.build_l1
build_verify    = V.build_verify
warmup_models   = V.warmup_models
q_block         = V.q_block
majority_vote   = V.majority_vote
DEFAULT_CFG     = V.DEFAULT_CFG
GESTALT_LIVE    = V.OUT

# mesh 专用答案抽取(覆盖 "Refined Verdict" / "Final Verdict" / "Verdict")
VERDICT_RE = re.compile(
    r"(?:refined verdict|final verdict|verdict|最终答案|裁定答案|answer|final)\s*[:：]\s*\(?([A-D])",
    re.I)
def extract_verdict(text):
    if not text:
        return None
    m = VERDICT_RE.search(text)
    if m:
        return m.group(1)
    m = V.LETTER_RE.search(text)  # 兜底: 首个独立字母
    return m.group(1) if m else None


# ---------- mesh 专用提示词 ----------
def build_l2_lateral(q, own_brief, own_resid, own_verdict, peers_text, conn_w):
    return (q_block(q) +
            f"[YOUR GROUP — Aggregation Brief]\n{own_brief.strip()}\n\n"
            f"[YOUR GROUP — Residual/Disagreements]\n{own_resid.strip()}\n\n"
            f"[YOUR GROUP — Deputy Verdict] {own_verdict.strip()}\n\n"
            "=== CROSS-GROUP PEER INPUT (other deputy groups' briefs & verdicts) ===\n"
            f"{peers_text.strip()}\n\n"
            f"Cross-layer connection strength = {conn_w:.2f} "
            "(0 = ignore peers; 1 = fully exploit cross-group signal).\n"
            "You are the DEPUTY brain of your group. Cross-pollinate with peers: reconcile "
            "disagreements, adopt any peer insight your group missed, and issue a REFINED group verdict.\n"
            "Format:\nRefined Verdict: <letter>\nReasoning: <one sentence>")


def build_l2_feedback(q, own_refined, prelim_text, conn_w):
    return (q_block(q) +
            f"[YOUR GROUP — Refined Verdict] {own_refined.strip()}\n\n"
            "=== CHIEF BRAIN'S PRELIMINARY SYNTHESIS (across all groups) ===\n"
            f"{prelim_text.strip()}\n\n"
            f"Cross-layer connection strength = {conn_w:.2f}.\n"
            "You are the DEPUTY brain. The CHIEF's preliminary answer is above. Re-examine: "
            "agree, or hold a valuable dissent the CHIEF overlooked? Issue your FINAL group verdict (may revise).\n"
            "Format:\nFinal Verdict: <letter>\nReasoning: <one sentence>")


def build_l3_lateral(q, persona, own_resp, peers_text, conn_w):
    """集群内部全连接(文档 5.1): 同组专家互看首轮答案再精炼, 抬 L3 层 αₘ。"""
    return (q_block(q) +
            f"[YOUR first-pass answer]\n{own_resp.strip()}\n\n"
            "=== PEER EXPERTS' FIRST-PASS ANSWERS (within your cluster) ===\n"
            f"{peers_text.strip()}\n\n"
            f"Connection strength = {conn_w:.2f}.\n"
            "You are a specialist in the cluster. Cross-check with peers: resolve disagreement, "
            "adopt any insight you missed, and give your FINAL answer.\n"
            "Format:\nAnswer: <letter>\nReason: <one sentence>")


# ---------- 组级阶段(两种拓扑共用) ----------
def run_group_phase(q, cfg, conn_w, n_l3, group_size, l3_lateral=False):
    """L3专家 -> (可选: 集群内全连横向精炼) -> 聚合(双通道) -> L2副脑(首轮裁定)。"""
    idxs_all = list(range(n_l3))
    groups = [idxs_all[i:i + group_size] for i in range(0, n_l3, group_size)]
    group_briefs, group_residuals, group_verdicts, group_choices, l3_choices, l3_choices_firstpass = [], [], [], [], [], []
    for gi, idxs in enumerate(groups):
        l3 = []
        for j in idxs:
            persona = persona_at(j)
            resp = generate(build_l3(q, persona), persona, cfg, model=cfg["l3_model"])
            l3.append((persona.split('.')[0], resp))
        l3_firstpass = [extract_choice(r[1]) for r in l3]   # 首轮(横向精炼前)答案, 拓扑不变多样性基线
        if l3_lateral and len(idxs) > 1:
            # 集群内部全连接: 同组专家互看首轮答案再精炼(文档 5.1)
            refined = []
            for j_idx, j in enumerate(idxs):
                peers = [l3[m][1] for m in range(len(idxs)) if m != j_idx]
                peers_text = "\n\n".join(f"[Peer expert {m+1} first-pass]\n{p}" for m, p in enumerate(peers))
                r2 = generate(build_l3_lateral(q, persona_at(j), l3[j_idx][1], peers_text, conn_w),
                              persona_at(j), cfg, model=cfg["l3_model"])
                refined.append((persona_at(j).split('.')[0], r2))
            l3 = refined
        l3_choices.extend(extract_choice(r[1]) for r in l3)
        l3_choices_firstpass.extend(l3_firstpass)
        agg_resp = generate(build_agg(q, l3), "You are the aggregation layer.", cfg, model=cfg["agg_model"])
        m = re.search(r"Disagreements\s*&\s*Residual\s*[:：](.*)", agg_resp, re.I | re.S)
        if m:
            brief = agg_resp[:m.start()].replace("Aggregation Brief", "").strip()
            residual = m.group(1).strip()
        else:
            brief, residual = agg_resp.strip(), "(none extracted)"
        l2_resp = generate(build_l2(q, brief, residual, conn_w), "You are the deputy brain.", cfg, model=cfg["l2_model"])
        l2_choice = extract_verdict(l2_resp)
        v2 = generate(build_verify(q, l2_choice or "?"), "You are a verifier.", cfg, model=cfg["verifier_model"])
        group_verdicts.append(l2_resp.strip())
        group_briefs.append(brief)
        group_residuals.append(residual)
        group_choices.append(l2_choice)
    return {"group_briefs": group_briefs, "group_residuals": group_residuals,
            "group_verdicts": group_verdicts, "group_choices": group_choices,
            "l3_choices": l3_choices, "l3_choices_firstpass": l3_choices_firstpass,
            "n_groups": len(groups)}


def tree_final(q, cfg, conn_w, gp):
    """tree 拓扑: 各组裁定直接汇总给 L1 主脑终裁(复刻 stage3)。"""
    combined_brief = "\n\n".join(f"[Group {i+1} aggregation brief]\n{b}" for i, b in enumerate(gp["group_briefs"]))
    combined_resid = "\n\n".join(f"[Group {i+1} residual]\n{r}" for i, r in enumerate(gp["group_residuals"]))
    group_text     = "\n\n".join(f"[Group {i+1} deputy verdict]\n{v}" for i, v in enumerate(gp["group_verdicts"]))
    l1_resp = generate(build_l1(q, combined_brief, combined_resid, group_text, conn_w),
                       "You are the chief brain.", cfg, model=cfg["orchestrator_model"])
    l1_choice = extract_choice(l1_resp)
    v1 = generate(build_verify(q, l1_choice or "?"), "You are a verifier.", cfg, model=cfg["verifier_model"])
    if ("FAIL" in (v1 or "").upper()) and l1_choice:
        l1_resp = generate(build_l1(q, combined_brief, combined_resid, group_text, conn_w) +
                           "\n(The previous answer failed verification. Re-check and give a confident final.)",
                           "You are the chief brain.", cfg, model=cfg["orchestrator_model"])
        l1_choice = extract_choice(l1_resp)
    return l1_choice


def mesh_final(q, cfg, conn_w, gp):
    """mesh 拓扑: (a) L2 横向全连网格精炼; (b) 主脑多跳(P1初步 -> 副脑反馈 -> P2终裁)。"""
    n_groups = gp["n_groups"]
    # (a) 横向全连: 每个副脑看到其他所有组的简报+裁定, 精炼
    refined = []
    for gi in range(n_groups):
        peers = []
        for gj in range(n_groups):
            if gj == gi:
                continue
            peers.append(f"[Group {gj+1} brief]\n{gp['group_briefs'][gj]}\n[Group {gj+1} verdict] {gp['group_verdicts'][gj]}")
        peers_text = "\n\n".join(peers)
        r = generate(build_l2_lateral(q, gp["group_briefs"][gi], gp["group_residuals"][gi],
                                     gp["group_verdicts"][gi], peers_text, conn_w),
                     "You are the deputy brain (cross-group).", cfg, model=cfg["l2_model"])
        refined.append(extract_verdict(r))
    # (b) 主脑多跳: 初步综合
    refined_text = "\n\n".join(f"[Group {i+1} refined verdict] {v}" for i, v in enumerate(refined))
    prelim = generate(build_l1(q,
                     "\n\n".join(f"[Group {i+1} brief]\n{b}" for i, b in enumerate(gp["group_briefs"])),
                     "\n\n".join(f"[Group {i+1} residual]\n{r}" for i, r in enumerate(gp["group_residuals"])),
                     refined_text, conn_w),
                     "You are the chief brain (preliminary).", cfg, model=cfg["orchestrator_model"])
    # (b) 副脑二次精炼(看到主脑初步)
    final_choices = []
    for gi in range(n_groups):
        r = generate(build_l2_feedback(q, refined[gi], prelim, conn_w),
                     "You are the deputy brain (final pass).", cfg, model=cfg["l2_model"])
        final_choices.append(extract_verdict(r))
    # (b) 主脑终裁
    final_text = "\n\n".join(f"[Group {i+1} final verdict] {v}" for i, v in enumerate(final_choices))
    l1_resp = generate(build_l1(q,
                     "\n\n".join(f"[Group {i+1} brief]\n{b}" for i, b in enumerate(gp["group_briefs"])),
                     "\n\n".join(f"[Group {i+1} residual]\n{r}" for i, r in enumerate(gp["group_residuals"])),
                     final_text, conn_w),
                     "You are the chief brain (final).", cfg, model=cfg["orchestrator_model"])
    l1_choice = extract_choice(l1_resp)
    v1 = generate(build_verify(q, l1_choice or "?"), "You are a verifier.", cfg, model=cfg["verifier_model"])
    if ("FAIL" in (v1 or "").upper()) and l1_choice:
        l1_resp = generate(build_l1(q,
                     "\n\n".join(f"[Group {i+1} brief]\n{b}" for i, b in enumerate(gp["group_briefs"])),
                     "\n\n".join(f"[Group {i+1} residual]\n{r}" for i, r in enumerate(gp["group_residuals"])),
                     final_text, conn_w) +
                     "\n(The previous answer failed verification. Re-check and give a confident final.)",
                     "You are the chief brain (final).", cfg, model=cfg["orchestrator_model"])
        l1_choice = extract_choice(l1_resp)
    return l1_choice


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
        tmp = Path(path).with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except Exception as e:
        sys.stderr.write(f"[live write fail] {e}\n"); sys.stderr.flush()


def topology_desc(topology, n_groups, group_sizes):
    if topology == "tree":
        return {"topology": "tree", "lateral_edges": 0,
                "cross_layer_hops": 1, "note": "树状分层(无跨组/集群内连接)"}
    l2_lat = n_groups * (n_groups - 1)                     # 副脑横向全连(有向)
    l3_lat = sum(s * (s - 1) for s in group_sizes) if topology == "full" else 0
    return {"topology": topology,
            "lateral_edges": l2_lat + l3_lat,
            "l2_lateral_edges": l2_lat, "l3_lateral_edges": l3_lat,
            "cross_layer_hops": 2,
            "note": "L2副脑全连 + 主脑多跳(深度2)" + (" + L3集群内全连" if topology == "full" else "")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--benchmark", default="benchmark/mcq_medium_clean.jsonl")
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--n-l3", type=int, default=20, help="L3 专家节点数 (1.5b)")
    ap.add_argument("--group-size", type=int, default=3, help="每几个 L3 配 1 个 L2 副脑")
    ap.add_argument("--conn-w", type=float, default=1.0)
    ap.add_argument("--topology", choices=["tree", "mesh", "full"], default="mesh",
                    help="tree=树状(复刻stage3); mesh=L2全连+主脑多跳; full=mesh+L3集群内全连")
    ap.add_argument("--live", default=str(GESTALT_LIVE / "stage4_topo_live.json"))
    ap.add_argument("--ablation", default="none",
                    help="none=7b主脑; demote=3b主脑+7b降级进L3集群; remove=无7b,3b主脑")
    ap.add_argument("--no-solo", action="store_true", help="跳过 7b solo 基线")
    args = ap.parse_args()

    cfg = dict(DEFAULT_CFG)
    cfg["k"] = args.n_l3
    if args.ablation == "demote":
        cfg["orchestrator_model"] = "qwen2.5:3b"
        cfg["participant_models"] = ["qwen2.5:7b"]
    elif args.ablation == "remove":
        cfg["orchestrator_model"] = "qwen2.5:3b"
        cfg["participant_models"] = []
    else:
        cfg["orchestrator_model"] = cfg["l1_model"]
        cfg["participant_models"] = []

    n_groups = math.ceil(args.n_l3 / args.group_size)
    group_sizes = [args.group_size] * (n_groups - 1)
    last = args.n_l3 - args.group_size * (n_groups - 1)
    if last > 0:
        group_sizes.append(last)
    tdesc = topology_desc(args.topology, n_groups, group_sizes)
    print(f"[stage4] topology={args.topology} n_l3={args.n_l3} group_size={args.group_size} "
          f"-> L2副脑数={n_groups} 主脑={cfg['orchestrator_model']} 消融={args.ablation} "
          f"n={args.n} conn_w={args.conn_w} | Ẇ代理: 横向边={tdesc['lateral_edges']} 跳数={tdesc['cross_layer_hops']}",
          flush=True)

    warmup_models(cfg)
    root = V.ROOT
    questions = load_questions(str(root / args.benchmark), args.n)
    if not questions:
        print("[stage4] 无题目, 退出"); return
    for i, q in enumerate(questions):
        q.setdefault("id", f"q{i+1}")

    live = {"phase": "init", "progress": "", "status": "running",
            "node_model": f"topo={args.topology} n_l3={args.n_l3} gs={args.group_size}",
            "n_l3": args.n_l3, "group_size": args.group_size, "n_groups": n_groups,
            "topology": args.topology, "topo_desc": tdesc,
            "current_w": args.conn_w,
            "collective_acc": {"cw1.00": None}, "node_acc": {}, "committee0": None,
            "samples": []}
    write_live(args.live, live)

    # ---- 7b solo 基线 (best_single) ----
    best_single = None
    if not args.no_solo:
        live["phase"] = "solo 7b (best_single)"
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
        live["A_net0"] = None
        print(f"[stage4] 7b solo best_single = {best_single:.4f}", flush=True)

    # ---- 集体(树状或扩拓扑) ----
    live["phase"] = f"collective ({args.topology})"
    write_live(args.live, live)
    correct = 0
    comm0_correct = 0
    comm0_fp_correct = 0
    samples = []
    t0 = time.time()
    for i, q in enumerate(questions):
        try:
            gp = run_group_phase(q, cfg, args.conn_w, args.n_l3, args.group_size,
                                 l3_lateral=(args.topology == "full"))
            if args.topology in ("mesh", "full"):
                l1 = mesh_final(q, cfg, args.conn_w, gp)
            else:
                l1 = tree_final(q, cfg, args.conn_w, gp)
            l3c = gp["l3_choices"]
            l3c_fp = gp["l3_choices_firstpass"]
            comm0 = majority_vote(l3c, tiebreak=l3c[0] if l3c else None)
            comm0_fp = majority_vote(l3c_fp, tiebreak=l3c_fp[0] if l3c_fp else None)
        except Exception as e:
            sys.stderr.write(f"[q{i}] pipeline error: {e}\n"); sys.stderr.flush()
            l1 = None; comm0 = None
        ok = (l1 == q.get("answer"))
        if ok:
            correct += 1
        if comm0 is not None and comm0 == q.get("answer"):
            comm0_correct += 1
        if comm0_fp is not None and comm0_fp == q.get("answer"):
            comm0_fp_correct += 1
        samples.append({"q": i, "l1": l1, "gold": q.get("answer"), "ok": ok,
                        "comm0": comm0, "comm0_firstpass": comm0_fp})
        acc = correct / (i + 1)
        comm0_acc = comm0_correct / (i + 1)
        comm0_fp_acc = comm0_fp_correct / (i + 1)
        live["collective_acc"] = {"cw1.00": acc}
        live["committee0"] = round(comm0_acc, 4)
        live["committee0_firstpass"] = round(comm0_fp_acc, 4)
        live["A_net0"] = round(comm0_acc, 4)
        live["progress"] = f"collective q {i+1}/{len(questions)}"
        write_live(args.live, live)
        if (i + 1) % 10 == 0:
            el = time.time() - t0
            sys.stderr.write(f"[collective {args.topology}] {i+1}/{len(questions)} acc={acc:.3f} "
                             f"comm0={comm0_acc:.3f} comm0_fp={comm0_fp_acc:.3f} elapsed={el/60:.1f}min\n"); sys.stderr.flush()

    acc = correct / len(questions)
    comm0_acc = comm0_correct / len(questions)
    comm0_fp_acc = comm0_fp_correct / len(questions)
    G = acc - comm0_acc
    live["collective_acc"] = {"cw1.00": acc}
    live["committee0"] = round(comm0_acc, 4)
    live["committee0_firstpass"] = round(comm0_fp_acc, 4)
    live["A_net0"] = round(comm0_acc, 4)
    live["phase"] = "done"
    live["status"] = "done"
    live["samples"] = samples
    live["node_acc"] = {"best_single_7b": best_single} if best_single is not None else live.get("node_acc", {})
    delta_vs_7b = (acc - best_single) if best_single is not None else None
    live["summary"] = {
        "topology": args.topology, "topo_desc": tdesc,
        "collective": acc, "committee0_L3vote": comm0_acc,
        "committee0_firstpass_L3vote": comm0_fp_acc,
        "G_collective_minus_comm0": G,
        "best_single_7b": best_single, "delta_vs_7b": delta_vs_7b,
        "n_l3": args.n_l3, "n_groups": n_groups,
        "lateral_edges": tdesc["lateral_edges"], "cross_layer_hops": tdesc["cross_layer_hops"],
    }
    write_live(args.live, live)
    print(f"[stage4 DONE] topology={args.topology} collective={acc:.4f} "
          f"comm0(L3vote)={comm0_acc:.4f} G={G:+.4f} best_single_7b={best_single} "
          f"delta_vs_7b={delta_vs_7b:+.4f} | Ẇ代理: 横向边={tdesc['lateral_edges']} 跳数={tdesc['cross_layer_hops']}",
          flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback as _tb
        sys.stderr.write("[FATAL] " + _tb.format_exc()); sys.stderr.flush()
        try:
            _p = sys.argv[sys.argv.index("--live") + 1] if "--live" in sys.argv else str(GESTALT_LIVE / "stage4_topo_live.json")
            _st = {}
            if os.path.exists(_p):
                try: _st = json.loads(open(_p, encoding="utf-8").read())
                except Exception: pass
            _st["status"] = "error"; _st["error"] = _tb.format_exc(); _st["updated_at"] = time.strftime("%H:%M:%S")
            write_live(_p, _st)
        except Exception as _ee:
            sys.stderr.write(f"[FATAL write failed] {_ee}\n"); sys.stderr.flush()
        raise
