#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_stage4_scan.py — n=50 拓扑密度(Ẇ)三档扫描 (tree -> mesh -> full)
========================================================================
目的: 在同节点数/同基准下, 仅改拓扑结构, 隔离 Ẇ(跨层连接密度)对集体准确率的影响,
      检验方程 M = Σsᵢ + Σ(αₘ−βₘ)Ẇ²ᵐ 后半(涌现/干涉竞争)是否随密度非单调(存在 Wc 峰值)。

控制变量:
  - 模型 = verify_stage2.DEFAULT_CFG (原版 qwen2.5:1.5b/3b/7b), 与 band_ok 基准完全一致
  - 基准 = benchmark/mcq_midhard_clean.jsonl (250 题扩量版, band_ok=True)
  - 仅变 topology: tree(0 横向边/1跳) < mesh(L2全连/2跳) < full(+L3集群内全连/2跳)

稳健性:
  - 单实例原子锁(O_EXCL + OpenProcess 探活自愈合), 防并发/僵尸锁
  - 每档 checkpoint 续跑(每题落盘), 进程被 kill 重启从断点继续, 不丢进度
  - 每题 try/except 容错, 单题 generate 异常不中断整档
  - 总看板 gestalt_live/stage4_scan_live.json (供 dashboard.py 轮询)
"""
import sys, os, json, time, math, argparse
from pathlib import Path
import ctypes

SCRIPT_DIR = r"D:\方程验证\scripts"
sys.path.insert(0, SCRIPT_DIR)
import verify_stage4_topology as S4
import verify_stage2 as V

# ---------- 单实例锁 (OpenProcess 探活, 自愈合) ----------
LOCK = r"D:\方程验证\benchmark\stage4_scan.lock"

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
            return False  # 真有活实例
        # 僵尸锁 -> 清掉重占
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

# ---------- 路径 ----------
BENCH = r"D:\方程验证\benchmark\mcq_midhard_clean.jsonl"
OUT_DIR = Path(r"D:\方程验证\results")
CKPT_DIR = Path(r"D:\方程验证\benchmark")
LIVE = Path(V.OUT) / "stage4_scan_live.json"
TOPOS = ["tree", "mesh", "full"]

def write_live(d):
    try:
        tmp = LIVE.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
        os.replace(tmp, LIVE)
    except Exception as e:
        sys.stderr.write(f"[live write fail] {e}\n"); sys.stderr.flush()

def ckpt_path(name, n_l3):
    return CKPT_DIR / f"stage4_{name}_ckpt_nl3{n_l3}.json"

def load_ckpt(name, n, n_l3):
    p = ckpt_path(name, n_l3)
    # 向后兼容: n_l3=12 时若新命名文件不存在, 尝试旧名(无 n_l3 后缀)
    if not p.exists() and n_l3 == 12:
        old = CKPT_DIR / f"stage4_{name}_ckpt.json"
        if old.exists():
            p = old
    if p.exists():
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            if d.get("n") == n:
                return d
        except Exception:
            pass
    return {"n": n, "done": 0, "rows": []}

def save_ckpt(name, ck, n_l3):
    p = ckpt_path(name, n_l3)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(ck, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, p)

def main_scan(args):
    N = args.n
    N_L3 = args.n_l3
    GROUP_SIZE = 3
    CONN_W = 1.0

    cfg = dict(V.DEFAULT_CFG)
    cfg["k"] = N_L3
    cfg["orchestrator_model"] = cfg["l1_model"]  # 默认 none 消融: 7b 主脑

    n_groups = math.ceil(N_L3 / GROUP_SIZE)
    group_sizes = [GROUP_SIZE] * (n_groups - 1)
    last = N_L3 - GROUP_SIZE * (n_groups - 1)
    if last > 0:
        group_sizes.append(last)

    print(f"[scan] 启动: N={N} N_L3={N_L3} groups={n_groups} topo={TOPOS} bench={BENCH}", flush=True)
    sys.stderr.write(f"[scan] warmup models...\n"); sys.stderr.flush()
    S4.warmup_models(cfg)
    questions = S4.load_questions(BENCH, N)
    if not questions:
        print("[scan] 无题目, 退出"); return
    for i, q in enumerate(questions):
        q.setdefault("id", f"q{i+1}")

    # 初始 live (solo 阶段看板就有数据)
    write_live({
        "status": "running", "phase": "solo 7b (best_single)",
        "progress": "init", "current_topo": "solo", "n_l3": N_L3, "n": N,
        "solo_7b": None, "topos": {}, "updated_at": time.strftime("%H:%M:%S"),
    })

    # ---- 7b solo 基线 (跑一次, 三档共用) ----
    solo_ckpt = CKPT_DIR / "stage4_solo_ckpt.json"
    solo = None
    if solo_ckpt.exists():
        try:
            sd = json.loads(solo_ckpt.read_text(encoding="utf-8"))
            if sd.get("n") == N:
                solo = sd.get("best_single")
        except Exception:
            solo = None
    if solo is None:
        sys.stderr.write(f"[scan] 跑 7b solo 基线 ({N} 题)...\n"); sys.stderr.flush()
        c = 0
        for i, q in enumerate(questions):
            try:
                if S4.run_solo(q, cfg, cfg["l1_model"]) == q.get("answer"):
                    c += 1
            except Exception:
                pass
            if (i + 1) % 10 == 0:
                sys.stderr.write(f"[solo] {i+1}/{N}\n"); sys.stderr.flush()
        solo = c / len(questions)
        solo_ckpt.write_text(json.dumps({"n": N, "best_single": solo}, ensure_ascii=False), encoding="utf-8")
    print(f"[scan] 7b solo best_single = {solo:.4f}", flush=True)

    topo_summaries = {}
    for topo in TOPOS:
        sys.stderr.write(f"[scan] === {topo} 开始 ===\n"); sys.stderr.flush()
        ck = load_ckpt(topo, N, N_L3)
        correct = sum(1 for r in ck["rows"] if r.get("ok"))
        comm0_correct = sum(1 for r in ck["rows"] if r.get("comm0_ok"))
        comm0_fp_correct = sum(1 for r in ck["rows"] if r.get("comm0_fp_ok"))
        t0 = time.time()
        for i in range(ck["done"], len(questions)):
            q = questions[i]
            try:
                gp = S4.run_group_phase(q, cfg, CONN_W, N_L3, GROUP_SIZE,
                                        l3_lateral=(topo == "full"))
                if topo in ("mesh", "full"):
                    l1 = S4.mesh_final(q, cfg, CONN_W, gp)
                else:
                    l1 = S4.tree_final(q, cfg, CONN_W, gp)
                l3c = gp["l3_choices"]
                l3c_fp = gp["l3_choices_firstpass"]
                comm0 = V.majority_vote(l3c, tiebreak=l3c[0] if l3c else None)
                comm0_fp = V.majority_vote(l3c_fp, tiebreak=l3c_fp[0] if l3c_fp else None)
            except Exception as e:
                sys.stderr.write(f"[q{i} {topo}] pipeline error: {e}\n"); sys.stderr.flush()
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
            save_ckpt(topo, ck, N_L3)
            acc = correct / (i + 1)
            comm0_acc = comm0_correct / (i + 1)
            comm0_fp_acc = comm0_fp_correct / (i + 1)
            write_live({
                "status": "running", "phase": f"collective ({topo})",
                "progress": f"{topo} {i+1}/{N}",
                "current_topo": topo, "n_l3": N_L3, "n": N,
                "solo_7b": round(solo, 4),
                "topos": {**{t: topo_summaries[t] for t in topo_summaries},
                          topo: {"done": i + 1, "acc": round(acc, 4),
                                 "comm0": round(comm0_acc, 4),
                                 "comm0_fp": round(comm0_fp_acc, 4)}},
                "updated_at": time.strftime("%H:%M:%S"),
            })
            if (i + 1) % 5 == 0:
                el = time.time() - t0
                sys.stderr.write(f"[collective {topo}] {i+1}/{N} acc={acc:.3f} "
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
            "best_single_7b": round(solo, 4),
            "delta_vs_7b": round(acc - solo, 4) if solo is not None else None,
            "n_l3": N_L3, "n_groups": n_groups, "n": N,
            "lateral_edges": tdesc["lateral_edges"],
            "cross_layer_hops": tdesc["cross_layer_hops"],
        }
        topo_summaries[topo] = summary
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        (OUT_DIR / f"stage4_{topo}_final_nl3{N_L3}.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[scan DONE] {topo}: collective={acc:.4f} comm0={comm0_acc:.4f} "
              f"G={G:+.4f} delta_vs_7b={acc-solo:+.4f} | Ẇ 横向边={tdesc['lateral_edges']} 跳数={tdesc['cross_layer_hops']}",
              flush=True)
        write_live({
            "status": "running", "phase": f"collective ({topo}) done",
            "progress": f"{topo} {N}/{N} done",
            "current_topo": topo, "n_l3": N_L3, "n": N,
            "solo_7b": round(solo, 4),
            "topos": {t: topo_summaries[t] for t in topo_summaries},
            "updated_at": time.strftime("%H:%M:%S"),
        })

    # 三档全完
    print("[scan] 全部完成. 汇总:", flush=True)
    for t in TOPOS:
        s = topo_summaries[t]
        print(f"  {t:5s}: collective={s['collective']:.4f} comm0={s['committee0_L3vote']:.4f} "
              f"G={s['G_collective_minus_comm0']:+.4f} delta_7b={s['delta_vs_7b']:+.4f} "
              f"lateral={s['lateral_edges']} hops={s['cross_layer_hops']}", flush=True)
    write_live({
        "status": "done", "phase": "scan complete",
        "progress": "tree/mesh/full 三档完成",
        "current_topo": "full", "n_l3": N_L3, "n": N,
        "solo_7b": round(solo, 4),
        "topos": {t: topo_summaries[t] for t in topo_summaries},
        "updated_at": time.strftime("%H:%M:%S"),
    })

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--n-l3", type=int, default=12, help="L3 专家节点数 (1.5b)")
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
