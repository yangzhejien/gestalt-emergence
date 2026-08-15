#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_p1_scan.py — P1 扩规模 + 密度联合扫描 (定位超线性临界 Wc)
========================================================================
目的: 在**更高难基准**(mcq_hard2_clean.jsonl) 上, 扫 节点数 n_l3 ∈ {20,30,40} × 拓扑 {tree,mesh,full},
      观察集体准确率(collective)在**什么规模/什么密度**第一次越过最强单体(best_single),
      即定位超线性涌现临界点 Wc 的实际落点。

与 run_stage4_scan.py 的区别:
  - 基准可配 (--bench), 不再硬编码 midhard
  - 所有产物按基准 stem 命名空间隔离, 不与 midhard 结果混/覆盖:
      p1_{topo}_ckpt_{stem}_nl3{N}.json
      p1_solo_ckpt_{stem}.json
      p1_{topo}_final_{stem}_nl3{N}.json
      p1_scan_live_{stem}.json
  - 支持 --n-l3 传单值或逗号列表(如 20,30,40), 内部顺序跑, 单实例锁贯穿

控制变量 / 稳健性: 同 stage4 (单实例原子锁自愈合 + 每题 checkpoint 续跑 + 单题容错 + live 看板)
"""
import sys, os, json, time, math, argparse
from pathlib import Path
import ctypes

SCRIPT_DIR = r"D:\方程验证\scripts"
sys.path.insert(0, SCRIPT_DIR)
import verify_stage4_topology as S4
import verify_stage2 as V

# ---------- 单实例锁 (OpenProcess 探活, 自愈合) ----------
LOCK = r"D:\方程验证\benchmark\p1_scan.lock"

def _pid_alive(pid):
    PROCESS_QUERY_INFORMATION = 0x0400
    PROCESS_VM_READ = 0x0010
    h = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if h == 0:
        return False
    ctypes.windll.kernel32.CloseHandle(h)
    return True

def acquire_single_instance():
    try:
        fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        old_pid = None
        try:
            old = open(LOCK).read().strip()
            old_pid = int(old.split()[0]) if old else None
        except Exception:
            old_pid = None
        if old_pid and _pid_alive(old_pid):
            return False
        try:
            os.remove(LOCK)
        except OSError:
            pass
        try:
            fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            return False
    os.write(fd, (str(os.getpid()) + "\n").encode())
    os.close(fd)
    return True

# ---------- 路径 (按基准 stem 隔离) ----------
OUT_DIR = Path(r"D:\方程验证\results")
CKPT_DIR = Path(r"D:\方程验证\benchmark")
TOPOS = ["tree", "mesh", "full"]

def write_live(stem, d):
    LIVE = CKPT_DIR / f"p1_scan_live_{stem}.json"
    try:
        tmp = LIVE.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
        os.replace(tmp, LIVE)
    except Exception as e:
        sys.stderr.write(f"[live write fail] {e}\n"); sys.stderr.flush()

def ckpt_path(stem, topo, n_l3):
    return CKPT_DIR / f"p1_{topo}_ckpt_{stem}_nl3{n_l3}.json"

def load_ckpt(stem, topo, n, n_l3):
    p = ckpt_path(stem, topo, n_l3)
    if p.exists():
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            if d.get("n") == n:
                return d
        except Exception:
            pass
    return {"n": n, "done": 0, "rows": []}

def save_ckpt(stem, topo, ck, n_l3):
    p = ckpt_path(stem, topo, n_l3)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(ck, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, p)

def main_scan(args):
    N = args.n
    stem = Path(args.bench).stem
    n_l3_list = [int(x) for x in str(args.n_l3).split(",") if x.strip()]

    print(f"[p1] 基准={args.bench} stem={stem} N={N} n_l3_list={n_l3_list} topo={TOPOS}", flush=True)
    sys.stderr.write(f"[p1] warmup models...\n"); sys.stderr.flush()
    S4.warmup_models(dict(V.DEFAULT_CFG))

    questions = S4.load_questions(args.bench, N)
    if not questions:
        print("[p1] 无题目, 退出"); return
    for i, q in enumerate(questions):
        q.setdefault("id", f"q{i+1}")

    # ---- 最强单体基线 (跑一次, 三层 solo 全测, 取最大为诚实基线; 按 stem 隔离) ----
    # 关键修正: 之前只测 7B 当 best_single, 但 midhard 上最强单体是 3B=0.79 (不是7B).
    # 机制B(超线性涌现) 的判据是「集体 > 最强单节点」, 故基线必须取 1.5B/3B/7B 三者 solo 最大值.
    solo_ckpt = CKPT_DIR / f"p1_solo_ckpt_{stem}.json"
    solo_data = None
    if solo_ckpt.exists():
        try:
            sd = json.loads(solo_ckpt.read_text(encoding="utf-8"))
            if sd.get("n") == N:
                solo_data = sd
        except Exception:
            solo_data = None
    if solo_data is None:
        sys.stderr.write(f"[p1] 跑三层单体基线 ({N} 题, 1.5B/3B/7B)...\n"); sys.stderr.flush()
        per_model = {}
        for key in ["l3_model", "l2_model", "l1_model"]:
            mname = V.DEFAULT_CFG[key]
            c = 0
            for i, q in enumerate(questions):
                try:
                    if S4.run_solo(q, V.DEFAULT_CFG, mname) == q.get("answer"):
                        c += 1
                except Exception:
                    pass
                if (i + 1) % 10 == 0:
                    sys.stderr.write(f"[solo {mname}] {i+1}/{N}\n"); sys.stderr.flush()
            per_model[mname] = c / len(questions)
        solo = max(per_model.values())
        solo_data = {"n": N, "best_single": solo, "per_model": per_model}
        solo_ckpt.write_text(json.dumps(solo_data, ensure_ascii=False), encoding="utf-8")
    solo = solo_data["best_single"]
    per_model = solo_data.get("per_model", {})
    print(f"[p1] 最强单体(best_single) = {solo:.4f}  三层solo: "
          f"{ {k: round(v,4) for k,v in per_model.items()} }", flush=True)

    # 铁律自检: 每层 sᵢ 必须 > 0.25 (随机地板). 若任一 <=0.25 则基准不合格, 告警.
    bad = {k: round(v,4) for k, v in per_model.items() if v <= 0.25}
    if bad:
        sys.stderr.write(f"[WARN] 基准违反铁律(每层sᵢ>0.25): {bad}\n"); sys.stderr.flush()

    write_live(stem, {
        "status": "running", "phase": "init", "progress": "solo done",
        "current_topo": "solo", "stem": stem, "n_l3_list": n_l3_list, "n": N,
        "best_single": round(solo, 4), "solo_per_model": {k: round(v,4) for k,v in per_model.items()},
        "topos": {}, "updated_at": time.strftime("%H:%M:%S"),
    })

    all_summaries = {}
    for N_L3 in n_l3_list:
        cfg = dict(V.DEFAULT_CFG)
        cfg["k"] = N_L3
        cfg["orchestrator_model"] = cfg["l1_model"]

        n_groups = math.ceil(N_L3 / 3)
        group_sizes = [3] * (n_groups - 1)
        last = N_L3 - 3 * (n_groups - 1)
        if last > 0:
            group_sizes.append(last)

        topo_summaries = {}
        for topo in TOPOS:
            sys.stderr.write(f"[p1 n_l3={N_L3}] === {topo} 开始 ===\n"); sys.stderr.flush()
            ck = load_ckpt(stem, topo, N, N_L3)
            correct = sum(1 for r in ck["rows"] if r.get("ok"))
            comm0_correct = sum(1 for r in ck["rows"] if r.get("comm0_ok"))
            comm0_fp_correct = sum(1 for r in ck["rows"] if r.get("comm0_fp_ok"))
            t0 = time.time()
            for i in range(ck["done"], len(questions)):
                q = questions[i]
                try:
                    gp = S4.run_group_phase(q, cfg, 1.0, N_L3, 3, l3_lateral=(topo == "full"))
                    if topo in ("mesh", "full"):
                        l1 = S4.mesh_final(q, cfg, 1.0, gp)
                    else:
                        l1 = S4.tree_final(q, cfg, 1.0, gp)
                    l3c = gp["l3_choices"]
                    l3c_fp = gp["l3_choices_firstpass"]
                    comm0 = V.majority_vote(l3c, tiebreak=l3c[0] if l3c else None)
                    comm0_fp = V.majority_vote(l3c_fp, tiebreak=l3c_fp[0] if l3c_fp else None)
                except Exception as e:
                    sys.stderr.write(f"[q{i} {topo} n{N_L3}] pipeline error: {e}\n"); sys.stderr.flush()
                    l1 = None; comm0 = None; comm0_fp = None
                ok = (l1 == q.get("answer"))
                comm0_ok = (comm0 is not None and comm0 == q.get("answer"))
                comm0_fp_ok = (comm0_fp is not None and comm0_fp == q.get("answer"))
                if ok:
                    correct += 1
                if comm0_ok:
                    comm0_correct += 1
                if comm0_fp_ok:
                    comm0_fp_correct += 1
                ck["rows"].append({"q": i, "l1": l1, "gold": q.get("answer"), "ok": ok,
                                   "comm0": comm0, "comm0_ok": comm0_ok,
                                   "comm0_fp": comm0_fp, "comm0_fp_ok": comm0_fp_ok})
                ck["done"] = i + 1
                save_ckpt(stem, topo, ck, N_L3)
                acc = correct / (i + 1)
                comm0_acc = comm0_correct / (i + 1)
                comm0_fp_acc = comm0_fp_correct / (i + 1)
                write_live(stem, {
                    "status": "running", "phase": f"collective ({topo}) n_l3={N_L3}",
                    "progress": f"{topo} n{N_L3} {i+1}/{N}",
                    "current_topo": topo, "stem": stem, "n_l3": N_L3, "n": N,
                    "best_single": round(solo, 4),
                    "topos": {**{f"{t}@nl3{N_L3}": topo_summaries[t] for t in topo_summaries},
                              f"{topo}@nl3{N_L3}": {"done": i + 1, "acc": round(acc, 4),
                                                    "comm0": round(comm0_acc, 4),
                                                    "comm0_fp": round(comm0_fp_acc, 4)}},
                    "updated_at": time.strftime("%H:%M:%S"),
                })
                if (i + 1) % 5 == 0:
                    el = time.time() - t0
                    sys.stderr.write(f"[collective {topo} n{N_L3}] {i+1}/{N} acc={acc:.3f} "
                                     f"comm0={comm0_acc:.3f} comm0_fp={comm0_fp_acc:.3f} "
                                     f"elapsed={el/60:.1f}min\n"); sys.stderr.flush()

            acc = correct / len(questions)
            comm0_acc = comm0_correct / len(questions)
            comm0_fp_acc = comm0_fp_correct / len(questions)
            G = acc - comm0_acc
            tdesc = S4.topology_desc(topo, n_groups, group_sizes)
            summary = {
                "topology": topo, "topo_desc": tdesc,
                "collective": round(acc, 4),
                "committee0_L3vote": round(comm0_acc, 4),
                "committee0_firstpass_L3vote": round(comm0_fp_acc, 4),
                "G_collective_minus_comm0": round(G, 4),
                "best_single": round(solo, 4),
                "solo_per_model": {k: round(v, 4) for k, v in per_model.items()},
                "delta_vs_best_single": round(acc - solo, 4),
                "beats_best": bool(acc > solo),
                "n_l3": N_L3, "n_groups": n_groups, "n": N,
                "lateral_edges": tdesc["lateral_edges"],
                "cross_layer_hops": tdesc["cross_layer_hops"],
            }
            topo_summaries[topo] = summary
            OUT_DIR.mkdir(parents=True, exist_ok=True)
            (OUT_DIR / f"p1_{topo}_final_{stem}_nl3{N_L3}.json").write_text(
                json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[p1 DONE n{N_L3}] {topo}: collective={acc:.4f} comm0={comm0_acc:.4f} "
                  f"G={G:+.4f} Δbest={acc-solo:+.4f} beats_best={acc>solo} "
                  f"| Ẇ 横向边={tdesc['lateral_edges']} 跳数={tdesc['cross_layer_hops']}", flush=True)
            write_live(stem, {
                "status": "running", "phase": f"collective ({topo}) n_l3={N_L3} done",
                "progress": f"{topo} n{N_L3} {N}/{N} done",
                "current_topo": topo, "stem": stem, "n_l3": N_L3, "n": N,
                "best_single": round(solo, 4),
                "topos": {f"{t}@nl3{N_L3}": topo_summaries[t] for t in topo_summaries},
                "updated_at": time.strftime("%H:%M:%S"),
            })
        all_summaries[N_L3] = topo_summaries

    # 全部完成
    print("[p1] 全部完成. 汇总 (按 n_l3 × topo):", flush=True)
    for N_L3 in n_l3_list:
        for t in TOPOS:
            s = all_summaries[N_L3][t]
            print(f"  n_l3={N_L3} {t:5s}: collective={s['collective']:.4f} "
                  f"comm0={s['committee0_L3vote']:.4f} G={s['G_collective_minus_comm0']:+.4f} "
                  f"Δbest={s['delta_vs_best_single']:+.4f} beats_best={s['beats_best']}", flush=True)
    write_live(stem, {
        "status": "done", "phase": "p1 scan complete",
        "progress": "全部 n_l3 × topo 完成",
        "current_topo": "full", "stem": stem, "n_l3_list": n_l3_list, "n": N,
        "best_single": round(solo, 4),
        "topos": {f"{t}@nl3{N_L3}": all_summaries[N_L3][t]
                  for N_L3 in n_l3_list for t in TOPOS},
        "updated_at": time.strftime("%H:%M:%S"),
    })

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", default=r"D:\方程验证\benchmark\mcq_midhard_clean.jsonl",
                    help="基准 jsonl 路径 (默认可信源 mcq_midhard_clean, 来自CEval真考题)")
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--n-l3", type=str, default="20,30,40",
                    help="L3 专家节点数, 单值或逗号列表 (如 20,30,40)")
    args = ap.parse_args()
    if not acquire_single_instance():
        print("已有实例在跑, 退出")
        sys.exit(0)
    try:
        main_scan(args)
    except Exception:
        import traceback as _tb
        sys.stderr.write("[FATAL] " + _tb.format_exc()); sys.stderr.flush()
    finally:
        try:
            os.remove(LOCK)
        except OSError:
            pass
