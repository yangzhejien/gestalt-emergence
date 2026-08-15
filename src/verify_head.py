#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
格式塔方程 头部验证 (a1*W^2 + a2*W^4 + a3*W^6; 低阶可弱, 高阶主导) — 带实时监测输出
=============================================================================
同质节点 qwen2.5:1.5b × k,通过本地 ollama HTTP API 推理。
实时把进度写入 data/live.json,供网页看板(dashboard.py)轮询展示。

流程:
  Round1: 每个节点(不同 persona)独立作答 -> a_i
  A_net(0): 节点独立答案的多数投票(委员会基线)
  Round2(w): 每个节点看到其他节点的 Round1 答案(按权重 w),
             修订后多数投票 -> A_net(w)
  G(w) = cap(A_net(w)) - cap(A_net(0))      # 纯连接增益(logit 空间)
  Ẇ(w) = 2w  (全连接, k 节点)
  拟合 G ≈ α1 Ẇ^2 + α2 Ẇ^4, 与线性零模型比较, 报 α 的 95% CI。
仅依赖标准库(urllib),避免 ollama python 包缺失。
控制台输出用 ASCII,避免 GBK 编码崩溃。
"""
import json, urllib.request, math, re, csv, os, sys, argparse, random, time
from pathlib import Path
import numpy as np

# 用 PYTHONUTF8=1 启动避免中文目录名乱码; 但后台任务的沙箱会拒绝写 D:\ ,
# 故实时数据写到沙箱允许的工作区目录 gestalt_live\ 下(纯英文, 无中文)。
ROOT = Path(__file__).resolve().parent.parent
OUT = Path(r"C:/Users/11409/WorkBuddy/2026-07-28-21-49-24/gestalt_live")
OUT.mkdir(parents=True, exist_ok=True)
LIVE_PATH = OUT / "live.json"


def load_config(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def generate(prompt, system, cfg, model=None, timeout=90):
    body = {
        "model": model if model else cfg["node_model"],
        "prompt": prompt,
        "system": system,
        "stream": False,
        "options": {"temperature": cfg.get("temperature", 0.0)},
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        cfg["ollama_url"], data=data, headers={"Content-Type": "application/json"}
    )
    last = None
    # 单次 90s 超时, 最多重试 2 次; 仍失败则兜底返回空串(该题记为跳过),
    # 绝不让单次 hung 的 ollama 请求拖死整个验证进程。
    for _ in range(2):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8")).get("response", "")
        except Exception as e:
            last = e
            sys.stderr.write(f"[generate retry] {e}\n")
            sys.stderr.flush()
            time.sleep(1)
    sys.stderr.write(f"[generate FAIL, treat as blank] {last}\n")
    sys.stderr.flush()
    return ""


LETTER_RE = re.compile(r"(?:^|[^A-Za-z])([A-D])(?:[^A-Za-z]|$)")
def extract_choice(text):
    if not text:
        return None
    m = re.search(r"(?:答案|answer)\s*[:is]+\s*\(?([A-D])\)?", text, re.I)
    if m:
        return m.group(1)
    m = LETTER_RE.search(text)
    return m.group(1) if m else None


def majority_vote(answers, tiebreak=None):
    counts, order = {}, []
    for a in answers:
        if a is None:
            continue
        if a not in counts:
            counts[a] = 0
            order.append(a)
        counts[a] += 1
    if not counts:
        return tiebreak
    best = max(counts.values())
    winners = [a for a in order if counts[a] == best]
    return winners[0] if len(winners) == 1 else (tiebreak if tiebreak is not None else winners[0])


def cap(p, clamp=1e-3):
    p = min(max(p, clamp), 1 - clamp)
    return math.log(p / (1 - p))


def solve_system(M, yv):
    """解线性系统 M x = yv (高斯消元, 返回 x)。"""
    n = len(yv)
    A = [row[:] + [yv[i]] for i, row in enumerate(M)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(A[r][c]))
        A[c], A[p] = A[p], A[c]
        piv = A[c][c]
        A[c] = [x / piv for x in A[c]]
        for r in range(n):
            if r != c:
                f = A[r][c]
                A[r] = [a - f * b for a, b in zip(A[r], A[c])]
    return [A[i][n] for i in range(n)]


def fit(terms, rows):
    """最小二乘拟合 G ≈ Σ coeff*Ẇ^t。用 numpy.linalg.lstsq (对秩亏稳健)。
    返回 (coeffs, r2); 若秩亏(列线性相关) r2 返回 nan。"""
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


def bootstrap_ci(rows, B=300, seed=0):
    """三阶偶次 bootstrap 置信区间: 返回 (lo1,hi1, lo2,hi2, lo3,hi3)。"""
    rng = random.Random(seed)
    a1s, a2s, a3s = [], [], []
    for _ in range(B):
        idx = [rng.randrange(len(rows)) for _ in range(len(rows))]
        sub = [rows[i] for i in idx]
        try:
            c, _ = fit([2, 4, 6], sub)
            a1s.append(c[0]); a2s.append(c[1]); a3s.append(c[2])
        except Exception:
            pass
    if not a1s:
        return (float("nan"),) * 6
    a1s.sort(); a2s.sort(); a3s.sort()
    n = len(a1s)
    return (a1s[int(0.025 * n)], a1s[int(0.975 * n)],
            a2s[int(0.025 * n)], a2s[int(0.975 * n)],
            a3s[int(0.025 * n)], a3s[int(0.975 * n)])


def save_live(state):
    state["updated_at"] = time.strftime("%H:%M:%S")
    try:
        tmp = LIVE_PATH.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        os.replace(tmp, LIVE_PATH)
    except Exception as e:
        sys.stderr.write(f"[save_live ERROR] {e}  path={LIVE_PATH}\n")
        sys.stderr.flush()


def build_prompt(q, others=None, w=None):
    base = f"Question: {q['question']}\n"
    for opt in ["A", "B", "C", "D"]:
        base += f"{opt}. {q[opt]}\n"
    base += "Answer with ONLY the single letter (A/B/C/D) of the correct option."
    if others:
        base += "\n\nOther agents independently answered (connection weight {}):\n".format(w)
        for j, ans in others:
            if ans:
                base += f"- Agent {j}: {ans}\n"
        base += "Consider their views, then give your own final answer (single letter only)."
    return base


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="verify_config.json", help="配置文件名(configs/下)")
    ap.add_argument("--n", type=int, default=None, help="题数(默认用配置)")
    ap.add_argument("--w", type=str, default=None, help="逗号分隔的 w 档")
    ap.add_argument("--tag", type=str, default="", help="输出文件名后缀")
    ap.add_argument("--live", default="live.json", help="实时数据文件名(避免覆盖其他轮)")
    ap.add_argument("--no-live", action="store_true", help="不写 live.json")
    args = ap.parse_args()

    global LIVE_PATH
    LIVE_PATH = OUT / args.live

    cfg = load_config(ROOT / "configs" / args.config)
    k = cfg["k"]
    personas = cfg["personas"][:k]
    # 异质支持: 若配置 node_models(列表)则按节点分配, 不足 k 个则循环补齐
    nm_cfg = cfg.get("node_models")
    if isinstance(nm_cfg, list) and nm_cfg:
        node_models = [nm_cfg[i % len(nm_cfg)] for i in range(k)]
    else:
        node_models = [cfg["node_model"]] * k
    w_levels = [float(x) for x in args.w.split(",")] if args.w else cfg["w_levels"]
    n_q = args.n if args.n else cfg["n_questions"]

    bench_path = ROOT / cfg["benchmark"]
    questions = []
    with open(bench_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                questions.append(json.loads(line))
    if n_q < len(questions):
        questions = questions[:n_q]
    print(f"[info] node_models={node_models} k={k} n={len(questions)} w={w_levels}")

    # 提前加载 live.json, 用于断点续跑(必须在 state 初始化前, 避免 Round1 写盘清空已有点)
    saved = None
    if LIVE_PATH.exists():
        try:
            saved = json.loads(LIVE_PATH.read_text(encoding="utf-8"))
        except Exception:
            saved = None
    use_saved_round1 = False
    if saved and isinstance(saved.get("round1_answers"), list) and len(saved["round1_answers"]) == k:
        use_saved_round1 = all(
            isinstance(a, list) and len(a) == len(questions) for a in saved["round1_answers"]
        )
    saved_points = saved.get("points") if (use_saved_round1 and isinstance(saved.get("points"), list)) else []

    state = {
        "status": "running", "phase": "init",
        "node_model": node_models, "k": k, "n_questions": len(questions),
        "w_levels": w_levels, "current_w": None,
        "current_node": None, "current_q": None, "progress": "",
        "node_acc": [None] * k, "A_net0": None,
        "points": list(saved_points), "fit": None, "judgement": "",
        "round1_answers": list(saved["round1_answers"]) if use_saved_round1 else [],
    }
    if not args.no_live:
        save_live(state)

    # Round1 (逐题写盘, 让看板真正实时滚动; 支持断点续跑)
    state["phase"] = "round1"; save_live(state)
    print("[round1] independent ...")
    round1 = []
    if use_saved_round1:
        round1 = [list(a) for a in saved["round1_answers"]]
        for i in range(k):
            acc = sum(1 for a, q in zip(round1[i], questions) if a == q["answer"]) / len(questions)
            state["node_acc"][i] = round(acc, 4)
        print("[round1] restored from live.json, skip regenerate")
        save_live(state)
    else:
        for i, persona in enumerate(personas):
            ans = []
            for ti, q in enumerate(questions):
                ans.append(extract_choice(generate(build_prompt(q), persona, cfg, model=node_models[i])))
                state["current_node"] = i
                state["current_q"] = ti
                state["progress"] = f"Round1 独立作答  node {i+1}/{k}  q {ti+1}/{len(questions)}"
                save_live(state)
            round1.append(ans)
            state["round1_answers"] = [list(x) for x in round1]  # 持久化, 支持崩溃续跑
            acc = sum(1 for a, q in zip(ans, questions) if a == q["answer"]) / len(questions)
            state["node_acc"][i] = round(acc, 4)
            print(f"  node{i} a_{i}={acc:.3f}")
            save_live(state)

    votes0 = [majority_vote([round1[i][ti] for i in range(k)], tiebreak=round1[0][ti])
              for ti in range(len(questions))]
    acc0 = sum(1 for a, q in zip(votes0, questions) if a == q["answer"]) / len(questions)
    state["A_net0"] = round(acc0, 4)
    print(f"[baseline] A_net(0)={acc0:.3f}")
    save_live(state)

    # Round2(w) (逐题写盘, 真正实时; 支持断点续跑: 跳过已完成的 w 档)
    rows = []
    done_w = set()
    if use_saved_round1 and saved and isinstance(saved.get("points"), list):
        for p in saved["points"]:
            rows.append(p); done_w.add(float(p["w"]))
    # 允许手动指定跳过某些 w 档(例如某档已物理跑完但未存点, 或曾崩于该档)
    if saved and isinstance(saved.get("force_skip_w"), list):
        for _wv in saved["force_skip_w"]:
            done_w.add(float(_wv))
    r2_total = sum(1 for w in w_levels if w != 0.0) * k * len(questions)
    r2_done = sum((0 if w == 0.0 else k * len(questions)) for w in done_w)
    for w in w_levels:
        if w in done_w:
            print(f"  skip w={w:.2f} (restored from live.json)")
            continue
        state["phase"] = "round2"; state["current_w"] = w
        state["current_node"] = None; state["current_q"] = None; save_live(state)
        if w == 0.0:
            a_net_w = votes0
        else:
            revised = []
            for i in range(k):
                rev = []
                for ti in range(len(questions)):
                    others = [(j, round1[j][ti]) for j in range(k) if j != i]
                    rev.append(extract_choice(generate(build_prompt(questions[ti], others=others, w=w), personas[i], cfg, model=node_models[i])))
                    r2_done += 1
                    state["current_node"] = i
                    state["current_q"] = ti
                    state["progress"] = f"Round2 连接修订  w={w:.2f}  node {i+1}/{k}  q {ti+1}/{len(questions)}  ({r2_done}/{r2_total})"
                    save_live(state)
                revised.append(rev)
            a_net_w = [majority_vote([revised[i][ti] for i in range(k)], tiebreak=round1[0][ti])
                       for ti in range(len(questions))]
        accw = sum(1 for a, q in zip(a_net_w, questions) if a == q["answer"]) / len(questions)
        What = 2.0 * w
        G = cap(accw) - cap(acc0)
        rows.append({"w": w, "What": What, "A_net0": acc0, "A_net_w": accw, "G": G})
        state["points"] = rows
        # 实时拟合(需 >=2 点)
        if len(rows) >= 2:
            c, r2 = fit([2, 4], rows)
            cl, r2l = fit([1], rows)
            fit_obj = {"alpha1": round(c[0], 4), "alpha2": round(c[1], 4),
                       "r2": (round(r2, 4) if not math.isnan(r2) else None),
                       "r2_lin": round(r2l, 4)}
            if math.isnan(r2):
                fit_obj["note"] = "参数不可辨识: 需≥3个w档才能区分α1/α2 (两点共线)"
            state["fit"] = fit_obj
        print(f"  w={w:.2f} W_hat={What:.3f} A_net(w)={accw:.3f} G={G:+.3f}")
        save_live(state)

    # 最终拟合 + CI (三阶偶次, 匹配"低阶不显/高阶主导"的设计)
    coeffs_cubic, r2_cubic = fit([2, 4, 6], rows)   # a1*Ẇ² + a2*Ẇ⁴ + a3*Ẇ⁶
    coeffs_quad, r2_quad = fit([2, 4], rows)        # 二阶(对比)
    coeffs_lin, r2_lin = fit([1], rows)             # 线性零模型
    lo1, hi1, lo2, hi2, lo3, hi3 = bootstrap_ci(rows)
    print(f"\n[fit] linear null        G~beta*W_hat            : beta={coeffs_lin[0]:+.4f}  R2={r2_lin:.4f}")
    print(f"[fit] quad (2nd+4th)      G~a1*W^2+a2*W^4          : a1={coeffs_quad[0]:+.4f} a2={coeffs_quad[1]:+.4f} R2={r2_quad:.4f}")
    print(f"[fit] cubic(2nd+4th+6th)  G~a1*W^2+a2*W^4+a3*W^6   : a1={coeffs_cubic[0]:+.4f} a2={coeffs_cubic[1]:+.4f} a3={coeffs_cubic[2]:+.4f} R2={r2_cubic:.4f}")

    # ===== 超线性检验 (Stage 1: 异质模型) =====
    # 方程头部 M = Σsᵢ + ΣαₘẆ²ᵐ。检验两件事(均同量纲, 可直接比较):
    #  (1) 连接协同增益 G_max = max_w[ cap(集体) - cap(断连委员会) ] > 0
    #      => 连接带来超出"独立投票汇总"的额外增益(即 ΣαẆ²ᵐ 项为正)
    #  (2) beats_best: 集体最优准确率 > 最强单模型准确率 => 涌现协同(团队胜最强成员)
    # 注: Σsᵢ=Σcap(individual) 是三节点对数胜率之和, 与单个集体cap计数不同、量纲不一致,
    #     故仅作理论参考, 不做差。正确的线性基准是"断连委员会" cap(committee0)。
    collective_max_acc = max(r["A_net_w"] for r in rows)
    opt_w = next(r["w"] for r in rows if r["A_net_w"] == collective_max_acc)
    G_max = max(r["G"] for r in rows)
    indiv_accs = [a for a in state["node_acc"] if a is not None]
    best_single = max(indiv_accs) if indiv_accs else 0.0
    linear_super = sum(cap(a) for a in indiv_accs)        # Σ sᵢ : 仅作理论参考(量纲不同)
    collective_cap = cap(collective_max_acc)              # M : 最优 w 下集体能力(对数胜率)
    beats_best = collective_max_acc > best_single
    super_ratio = (collective_max_acc / best_single) if best_single > 1e-6 else float("nan")
    print(f"[superlinear] best_single={best_single:.3f} committee0={acc0:.3f} collective_max@{opt_w:.2f}={collective_max_acc:.3f} G_max={G_max:+.3f}")
    print(f"[superlinear] Σsᵢ(参考,量纲不同)={linear_super:.3f} collective_cap={collective_cap:.3f} beats_best={beats_best}")

    # 判定: 核心是"高阶(>=4次)项是否显著为正"; 低阶(a1)弱/不显著是设计预期(不扣分)
    a3_sig = (not math.isnan(r2_cubic)) and (lo3 > 0)
    a2_sig = (not math.isnan(r2_cubic)) and (lo2 > 0)
    cubic_wins = (not math.isnan(r2_cubic)) and (r2_cubic > r2_lin)
    if cubic_wins and a3_sig:
        judge = "*** strong: 三阶偶次模型胜线性null, 且6次项(a3)95%CI不含0 -> 头部(含6次)成立; 低阶可弱, 符合设计."
    elif cubic_wins and a2_sig:
        judge = "** good: 三阶偶次模型胜线性null, 且4次项(a2)95%CI不含0 -> 头部到4次成立; 低阶可弱, 符合设计."
    elif cubic_wins:
        judge = "* partial: 三阶偶次模型胜线性null, 但高阶项CI含0(样本不足) -> 仅见趋势, 需更大n/更密w."
    else:
        judge = "*/0 数据不支持当前偶次形式; 需扩大n、加密w或修订方程."
    # 超线性结论附加(同量纲判据)
    if beats_best:
        judge += f"  [超线性] 集体({collective_max_acc:.3f})优于最强单模型({best_single:.3f}), 协同涌现成立."
    else:
        judge += f"  [未超线性] 集体({collective_max_acc:.3f})未超过最强单模型({best_single:.3f})."
    if G_max > 0:
        judge += f"  连接协同增益 G_max={G_max:+.3f}>0, 超越'独立投票汇总'(ΣαẆ²ᵐ项为正)."
    else:
        judge += f"  连接协同增益 G_max={G_max:+.3f}≤0, 未超越独立投票汇总."
    state["superlinear"] = {
        "best_single": round(best_single, 4), "committee0": round(acc0, 4),
        "collective_max": round(collective_max_acc, 4), "opt_w": opt_w,
        "G_max": round(G_max, 4),
        "linear_super_ref": round(linear_super, 4), "collective_cap": round(collective_cap, 4),
        "beats_best": beats_best,
        "super_ratio": (round(super_ratio, 4) if not (isinstance(super_ratio, float) and math.isnan(super_ratio)) else None),
    }
    state["fit"] = {"alpha1": round(coeffs_cubic[0], 4), "alpha2": round(coeffs_cubic[1], 4),
                    "alpha3": round(coeffs_cubic[2], 4),
                    "r2": (round(r2_cubic, 4) if not math.isnan(r2_cubic) else None),
                    "r2_quad": round(r2_quad, 4), "r2_lin": round(r2_lin, 4),
                    "alpha1_ci": [round(lo1, 4), round(hi1, 4)],
                    "alpha2_ci": [round(lo2, 4), round(hi2, 4)],
                    "alpha3_ci": [round(lo3, 4), round(hi3, 4)]}
    state["judgement"] = judge
    state["status"] = "done"; state["phase"] = "fit"
    save_live(state)

    # 落盘 CSV + 报告
    tag = ("_" + args.tag) if args.tag else ""
    data_path = OUT / f"verify_data{tag}.csv"
    with open(data_path, "w", newline="", encoding="utf-8") as f:
        wcsv = csv.writer(f)
        wcsv.writerow(["w", "What", "A_net0", "A_net_w", "G"])
        for r in rows:
            wcsv.writerow([r["w"], f"{r['What']:.4f}", f"{r['A_net0']:.4f}", f"{r['A_net_w']:.4f}", f"{r['G']:.4f}"])
    rep_path = OUT / f"verify_report{tag}.md"
    with open(rep_path, "w", encoding="utf-8") as f:
        f.write("# 格式塔方程头部验证报告\n\n")
        f.write(f"- 节点模型: {' / '.join(node_models)} (异质={len(set(node_models))>1})\n- 拓扑: {cfg['topology']} - 题数: {len(questions)}\n- 拟合项: a1*W^2 + a2*W^4 + a3*W^6 (低阶可弱, 高阶主导)\n\n")
        f.write("## 数据点\n| w | W_hat | A_net(0) | A_net(w) | G |\n")
        for r in rows:
            f.write(f"| {r['w']:.2f} | {r['What']:.3f} | {r['A_net0']:.3f} | {r['A_net_w']:.3f} | {r['G']:+.3f} |\n")
        f.write("\n## 拟合\n")
        f.write(f"- 线性零模型: beta={coeffs_lin[0]:+.4f}, R2={r2_lin:.4f}\n")
        f.write(f"- 二阶(2+4): a1={coeffs_quad[0]:+.4f}, a2={coeffs_quad[1]:+.4f}, R2={r2_quad:.4f}\n")
        f.write(f"- 三阶(2+4+6): a1={coeffs_cubic[0]:+.4f}, a2={coeffs_cubic[1]:+.4f}, a3={coeffs_cubic[2]:+.4f}, R2={r2_cubic:.4f}\n")
        f.write(f"- a1 95% CI: [{lo1:+.4f}, {hi1:+.4f}]  (低阶, 设计预期可弱/不显著)\n")
        f.write(f"- a2 95% CI: [{lo2:+.4f}, {hi2:+.4f}]  (4次项)\n")
        f.write(f"- a3 95% CI: [{lo3:+.4f}, {hi3:+.4f}]  (6次项)\n")
        f.write("\n## 超线性检验 (异质模型)\n")
        f.write(f"- 各节点独立准确率: {[round(a,3) for a in indiv_accs]}\n")
        f.write(f"- 最强单模型准确率: {best_single:.3f}\n")
        f.write(f"- 断连委员会 A_net(0): {acc0:.3f}\n")
        f.write(f"- 集体最优 (w={opt_w:.2f}, W_hat={2.0*opt_w:.2f}): {collective_max_acc:.3f}\n")
        f.write(f"- 连接协同增益 G_max = max[cap(集体)-cap(委员会0)] = {G_max:+.3f} -> {'>0 涌现协同成立' if G_max>0 else '<=0 未超越独立汇总'}\n")
        f.write(f"- 集体是否超过最强单模型: {'是' if beats_best else '否'} (准确率倍率 {super_ratio:.3f})\n")
        f.write(f"- 参考: Σsᵢ=Σcap(individual)={linear_super:.3f} (三节点对数胜率之和, 与单个集体cap量纲不同, 仅理论对照)\n")
        f.write(f"\n## 判定\n{judge}\n")
    print(f"\n[done] data -> {data_path}\n[done] report -> {rep_path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback as _tb
        _msg = _tb.format_exc()
        sys.stderr.write("[FATAL] " + _msg)
        sys.stderr.flush()
        try:
            _st = {}
            if LIVE_PATH.exists():
                try:
                    _st = json.loads(LIVE_PATH.read_text(encoding="utf-8"))
                except Exception:
                    pass
            _st["status"] = "error"
            _st["error"] = _msg
            _st["updated_at"] = time.strftime("%H:%M:%S")
            _tmp = LIVE_PATH.with_suffix(".tmp")
            with open(_tmp, "w", encoding="utf-8") as _f:
                json.dump(_st, _f, ensure_ascii=False, indent=2)
            os.replace(_tmp, LIVE_PATH)
        except Exception as _ee:
            sys.stderr.write(f"[FATAL write failed] {_ee}\n")
            sys.stderr.flush()
        raise
