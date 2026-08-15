#!/usr/bin/env python3
# probe_hard.py — 探针核验更高难度基准的合法性(方程物理前提)
# ─────────────────────────────────────────────────────────────────
# 用 1.5B / 3B / 7B 各自 solo 答题, 测难度:
#   接受带: 7B solo ∈ [0.45,0.65] (强模型远低于天花板, 给 ΣαₘẆ²ᵐ 留显示空间)
#           1.5B solo > 0.40      (最弱节点不贴地板, 保 sᵢ>0)
#   若 7B 偏易(>0.65) -> 自动裁剪(多留 7B 错的题)把率拉到 ~0.58
#   若 7B 偏难(<0.45) 或 1.5B 贴地板(<0.40) -> 告警, 建议重新生成
# 产出: benchmark/mcq_hard_clean.jsonl + benchmark/mcq_hard_probe.json
# 特性: 断点续跑(每题落 checkpoint) + 逐题异常重试(抗 Ollama 抖动)
# 用法: python probe_hard.py
# ─────────────────────────────────────────────────────────────────
import sys, os, json, argparse, time, math, random, ast, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify_stage2 as V
from verify_stage4_topology import run_solo
ROOT = V.ROOT

POOL = ROOT / "benchmark" / "mcq_hard_pool.jsonl"
OUT_CLEAN = ROOT / "benchmark" / "mcq_hard_clean.jsonl"
OUT_PROBE = ROOT / "benchmark" / "mcq_hard_probe.json"
CKPT = ROOT / "benchmark" / "mcq_hard_probe_ckpt.json"
SAMPLE_15B = 100  # 1.5B 抽样测量(省钱), 7B 全测; 池<100 时全测
LIVE = V.OUT / "probe_hard_live.json"  # 供看板实时显示探针进度

def write_live(d):
    try:
        tmp = LIVE.with_suffix(".tmp")
        tmp.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, LIVE)
    except Exception as e:
        sys.stderr.write(f"[probe live write fail] {e}\n"); sys.stderr.flush()

def load_ckpt():
    if CKPT.exists():
        try:
            d = json.loads(CKPT.read_text(encoding="utf-8"))
            return d.get("r7", []), d.get("r15", []), d.get("r3", [])
        except Exception:
            return [], [], []
    return [], [], []

def save_ckpt(r7, r15, r3):
    try:
        tmp = CKPT.with_suffix(".tmp")
        tmp.write_text(json.dumps({"r7": r7, "r15": r15, "r3": r3}, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, CKPT)
    except Exception as e:
        sys.stderr.write(f"[probe ckpt write fail] {e}\n"); sys.stderr.flush()

def safe_run_solo(qn, cfg, model, tries=3):
    """带重试的 solo 测量: Ollama 抖动时最多重试 tries 次; 全失败返回 None(记错但不崩)。"""
    last = None
    for t in range(tries):
        try:
            return run_solo(qn, cfg, model)
        except Exception as e:
            last = e
            sys.stderr.write(f"  [retry {t+1}/{tries}] {model} solo fail: {e}\n"); sys.stderr.flush()
            time.sleep(1.5 + t)
    sys.stderr.write(f"  [GAVEUP] {model} solo 连续失败, 记 None\n"); sys.stderr.flush()
    return None

def load_pool():
    qs = []
    for line in open(POOL, encoding="utf-8"):
        line = line.strip()
        if line:
            qs.append(json.loads(line))
    return qs

def normalize(q):
    """高难题库 schema {q, options, answer, rationale} -> run_solo 期望的
    {question, A, B, C, D, answer}。options 可能是 dict 或字符串 repr。"""
    opts = q.get("options")
    if isinstance(opts, str):
        try:
            opts = ast.literal_eval(opts)
        except Exception:
            opts = {}
    if not isinstance(opts, dict):
        opts = {}
    return {
        "question": q.get("q", q.get("question", "")),
        "A": opts.get("A"), "B": opts.get("B"),
        "C": opts.get("C"), "D": opts.get("D"),
        "answer": q.get("answer", q.get("A")),
    }

def main():
    global POOL, OUT_CLEAN, OUT_PROBE, CKPT, LIVE
    ap = argparse.ArgumentParser()
    ap.add_argument("--target-7b-lo", type=float, default=0.45)
    ap.add_argument("--target-7b-hi", type=float, default=0.65)
    ap.add_argument("--floor-15b", type=float, default=0.40)
    ap.add_argument("--floor-3b", type=float, default=0.25,
                    help="升级版铁律: 每层 sᵢ 都须 > 随机, L2(3B)中层也须 > 此值(防止死节点门控涌现)")
    ap.add_argument("--pool", default=str(POOL), help="题库路径(默认 mcq_hard_pool.jsonl)")
    ap.add_argument("--out-clean", default=str(OUT_CLEAN))
    ap.add_argument("--out-probe", default=str(OUT_PROBE))
    ap.add_argument("--live", default=str(LIVE))
    ap.add_argument("--no-resume", action="store_true", help="忽略断点从头跑")
    ap.add_argument("--sample-7b", type=int, default=0,
                    help="7B 抽样测题数(默认0=全测); 扩量大池时改用抽样加速验证")
    args = ap.parse_args()
    # 参数化路径(默认保持 hard 兼容); 全局重赋值让 load_pool/save_ckpt/write_live 自动跟随
    POOL = V.ROOT / "benchmark" / os.path.basename(args.pool)
    OUT_CLEAN = V.ROOT / "benchmark" / os.path.basename(args.out_clean)
    OUT_PROBE = V.ROOT / "benchmark" / os.path.basename(args.out_probe)
    CKPT = (V.ROOT / "benchmark" / os.path.basename(args.out_probe)).with_suffix(".ckpt.json")
    LIVE = V.OUT / os.path.basename(args.live)

    qs = load_pool()
    print(f"[probe_hard] pool={len(qs)}", flush=True)
    if len(qs) < 50:
        print("[probe_hard] 池太小, 先跑 gen_hard_benchmark"); return

    if args.no_resume and CKPT.exists():
        CKPT.unlink(); print("[probe_hard] 已清旧断点", flush=True)
    r7, r15, r3 = load_ckpt()
    print(f"[probe_hard] 断点: 7B={len(r7)} 15B={len(r15)} 3B={len(r3)} / 池{len(qs)}", flush=True)

    cfg = dict(V.DEFAULT_CFG)
    V.warmup_models(cfg)

    # ---- 7B 测量(可续跑, 支持抽样) ----
    idx7 = list(range(len(qs)))
    if args.sample_7b and args.sample_7b < len(qs):
        random.seed(7)
        idx7 = sorted(random.sample(range(len(qs)), args.sample_7b))
    if len(r7) >= len(idx7):
        print(f"[probe_hard] 7B 已完成(续跑跳过), acc={sum(r7)/len(r7):.3f}", flush=True)
    else:
        mode = f"抽样{len(idx7)}" if args.sample_7b else f"全池{len(idx7)}"
        print(f"[probe_hard] 测 7B solo ({mode}, 从 {len(r7)} 续)...", flush=True)
        for k in range(len(r7), len(idx7)):
            i = idx7[k]
            qn = normalize(qs[i])
            c = safe_run_solo(qn, cfg, cfg["l1_model"])
            r7.append(c == qn["answer"] if c is not None else False)
            done = k + 1
            if done % 25 == 0:
                print(f"  7B {done}/{len(idx7)} acc={sum(r7)/done:.3f}", flush=True)
            cur = sum(r7)/done
            write_live({
                "status": "running", "phase": "probe-7b",
                "progress": f"7B solo {done}/{len(idx7)} 当前acc={cur:.3f}",
                "n_questions": len(qs), "measured_7b": done,
                "node_acc": [cur], "updated_at": time.strftime("%H:%M:%S"),
            })
            save_ckpt(r7, r15, r3)
    acc7 = sum(r7)/len(r7)

    # ---- 1.5B / 3B 抽样(可续跑) ----
    idxs = list(range(len(qs)))
    random.seed(42)
    sample = sorted(random.sample(idxs, min(SAMPLE_15B, len(qs))))
    if len(r15) >= len(sample):
        print(f"[probe_hard] 1.5B/3B 已完成(续跑跳过), acc15={sum(r15)/len(r15):.3f} acc3={sum(r3)/len(r3):.3f}", flush=True)
    else:
        print(f"[probe_hard] 测 1.5B/3B solo (抽样 {len(sample)}, 从 {len(r15)} 续)...", flush=True)
        for n in range(len(r15), len(sample)):
            i = sample[n]
            qn = normalize(qs[i])
            c15 = safe_run_solo(qn, cfg, cfg["l3_model"])
            c3 = safe_run_solo(qn, cfg, cfg["l2_model"])
            r15.append(c15 == qn["answer"] if c15 is not None else False)
            r3.append(c3 == qn["answer"] if c3 is not None else False)
            if (n+1) % 25 == 0:
                print(f"  15B/3B {n+1}/{len(sample)} acc15={sum(r15)/(n+1):.3f} acc3={sum(r3)/(n+1):.3f}", flush=True)
            write_live({
                "status": "running", "phase": "probe-15b-3b",
                "progress": f"1.5B/3B 抽样 {n+1}/{len(sample)} acc15={sum(r15)/(n+1):.3f} acc3={sum(r3)/(n+1):.3f}",
                "n_questions": len(qs), "measured_7b": len(qs),
                "node_acc": [acc7, sum(r3)/(n+1), sum(r15)/(n+1)],
                "updated_at": time.strftime("%H:%M:%S"),
            })
            save_ckpt(r7, r15, r3)
    acc15 = sum(r15)/len(r15); acc3 = sum(r3)/len(r3)

    print(f"[probe_hard] 实测: 7B={acc7:.3f} 3B={acc3:.3f} 1.5B={acc15:.3f}", flush=True)

    # 选择最终集(目标 7B∈[lo,hi])
    TARGET = 0.58
    selected = []
    if args.sample_7b and args.sample_7b < len(qs):
        # 抽样验证模式: 裁剪需全池一一对应, 跳过; 直接接受全池供密度扫描使用
        selected = qs
        print(f"[probe_hard] 抽样验证模式: 不裁剪, 接受全池 {len(qs)} 题为 clean", flush=True)
    elif acc7 > args.target_7b_hi:
        wrong = [i for i in range(len(qs)) if not r7[i]]
        right = [i for i in range(len(qs)) if r7[i]]
        random.shuffle(right)
        k = int(round(TARGET * len(wrong) / (1 - TARGET)))
        k = min(k, len(right))
        keep = wrong + right[:k]
        selected = [qs[i] for i in sorted(keep)]
        est7 = len(wrong) / len(keep)
        print(f"[probe_hard] 偏易已裁剪: 保留 {len(selected)} 题, 估计7B率≈{est7:.3f}", flush=True)
    elif acc7 < args.target_7b_lo:
        print(f"[probe_hard] 警告: 7B={acc7:.3f} 偏难(可能把超线性项也压没), 建议重新生成更易的题", flush=True)
        selected = qs
    else:
        selected = qs
        print(f"[probe_hard] 7B 在目标带内, 全池接受为 hard_clean", flush=True)

    with open(OUT_CLEAN, "w", encoding="utf-8") as f:
        for q in selected:
            f.write(json.dumps(q, ensure_ascii=False) + "\n")

    probe = {
        "pool_size": len(qs),
        "acc_7b": round(acc7, 4), "acc_3b": round(acc3, 4), "acc_15b_sample": round(acc15, 4),
        "sample_15b_n": len(sample),
        "selected_size": len(selected),
        "band_ok": (args.target_7b_lo <= acc7 <= args.target_7b_hi) and (acc15 > args.floor_15b) and (acc3 > args.floor_3b),
        "floor_15b_ok": acc15 > args.floor_15b,
        "floor_3b_ok": acc3 > args.floor_3b,
        "note": "7B solo 全测; 1.5B/3B 为抽样估计; 支持断点续跑; band_ok 已纳入每层>随机(升级版铁律)",
    }
    json.dump(probe, open(OUT_PROBE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    # 清断点(已完成)
    if CKPT.exists(): CKPT.unlink()
    print(f"[probe_hard] DONE clean={OUT_CLEAN} ({len(selected)} 题) probe={OUT_PROBE}", flush=True)
    print(f"[probe_hard] band_ok={probe['band_ok']}", flush=True)
    write_live({
        "status": "done", "phase": "probe-final",
        "progress": f"完成: 7B={acc7:.3f} 3B={acc3:.3f} 1.5B={acc15:.3f} band_ok={probe['band_ok']}",
        "n_questions": len(qs), "measured_7b": len(qs),
        "node_acc": [acc7, acc3, acc15],
        "band_ok": probe["band_ok"], "floor_15b_ok": probe["floor_15b_ok"],
        "updated_at": time.strftime("%H:%M:%S"),
    })

if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        # 把崩溃信息也写进 live, 便于看板/排查
        write_live({
            "status": "error", "phase": "crashed",
            "progress": "探针异常崩溃, 见日志/ckpt(可续跑)",
            "updated_at": time.strftime("%H:%M:%S"),
        })
        raise
