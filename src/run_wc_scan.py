#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
格式塔方程 —— 补扫 Wc (严格钉方程 M(W) 峰位)
=============================================
背景:
  原密度扫描 run_density_scan.py 把 --conn-w 写死 1.0, 只扫 k(专家数) 作 W 的 proxy,
  与方程 M(W) 的 W(跨层连接强度 Ẇ) 轴错位 (见 2026-08-14 分析)。
  本脚本固定 k(Condorcet 征募数), 扫 Ẇ=conn_w 多档, 直接钉方程 M(W) 的 Wc 峰位。

关键澄清 (物理语义):
  方程 M(W) 的 W 操作化为 conn_w (verify_stage2.py line22: 跨层连接强度 Ẇ)。
  k 是 "独立专家数 / Condorcet 征募规模", 在此补扫中固定为调控参数。
  本补扫给出 M(Ẇ) 单峰曲线; 与原 k 扫描互补, 共同覆盖 W 的两个维度。
  (若未来发现 W 需 k×Ẇ 复合, 再扩展; 本脚本先严格钉单一操作化维度的峰位。)

执行:
  - 前置等待: 必须等 k20 密度扫描 done (否则与编排器抢 Ollama 互相饿死)
  - Ollama 探活 (down 时持续等待重试, 抗休眠带停)
  - 调用 verify_stage2.py 一次扫全部 Ẇ 档 (其内部题级断点续跑 + 已完成档重建, 抗崩溃)
  - done 后提取 collective_acc 各档 + G, 画 M(Ẇ) 曲线 + 输出 md 摘要

输出:
  OUT/stage2_wc_k{K}.json        (由 verify_stage2 写, 各 Ẇ 档集体准确率)
  OUT/wc_scan_k{K}.png           (M(Ẇ) 曲线图)
  OUT/wc_scan_report_k{K}.md     (各档表 + 判定说明)
"""
import json, subprocess, sys, time, os, urllib.request, argparse
from pathlib import Path

# 仓库根 = 本脚本上级目录 (src/ 的父目录)
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCRIPT = HERE / "verify_stage2.py"                       # 与编排器同目录
BENCH = ROOT / "data" / "mcq_medium_clean.jsonl"
OUT = ROOT / "results" / "live"                         # 默认输出到仓库内, 可复现不依赖本机路径
PY = sys.executable                                      # 用当前 python 解释器(无需硬编码路径)

# ===== 可调参数 =====
FIXED_K = 10                                  # 固定专家数 (已验证 bug3 稳定且 done)
CONN_LEVELS = "0.0,0.2,0.4,0.5,0.6,0.8,1.0"  # 扫 Ẇ 多档, 密覆盖预言 Wc≈0.45-0.62
N = 500
LIVE = f"stage2_wc_k{FIXED_K}.json"           # 独立 live 文件, 与密度扫描隔离
WAIT_LIVE = "stage2_density_k20.json"         # 等这个 done 才启动 (避免抢 Ollama)
WAIT_TIMEOUT = 7 * 24 * 3600                  # 最多等 7 天
# =====================


def ollama_ok(url="http://127.0.0.1:11434/api/tags", tries=20, gap=15):
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=10) as r:
                if r.status == 200:
                    return True
        except Exception:
            pass
        if i < tries - 1:
            time.sleep(gap)
    return False


LOCK = OUT / "wc_scan.lock"


def acquire_lock():
    """单实例保护: 避免后台机制重复启动导致 k20 done 时双跑 verify_stage2 冲突。

    用 PID 锁文件: 启动时若已有存活实例则立即退出; 旧 PID 已死则覆盖。
    进程正常退出时删除锁文件 (见 main 的 finally)。
    """
    try:
        if LOCK.exists():
            old = LOCK.read_text(encoding="utf-8").strip()
            try:
                opid = int(old)
                os.kill(opid, 0)  # Windows: sig=0 仅检查进程是否存在
                print(f"[wc] 已有实例运行 PID={opid}, 本进程退出(防双跑冲突)", flush=True)
                sys.exit(0)
            except (ValueError, OSError):
                pass  # 旧 PID 已死, 覆盖锁
        LOCK.write_text(str(os.getpid()), encoding="utf-8")
    except Exception as e:
        print(f"[wc] 锁检查异常(继续运行): {e}", flush=True)


def is_done(live):
    p = OUT / live
    if not p.exists():
        return False
    try:
        return json.loads(p.read_text(encoding="utf-8")).get("status") == "done"
    except Exception:
        return False


def wait_k20_done():
    print(f"[wc] 等待 {WAIT_LIVE} done (最多 {WAIT_TIMEOUT//86400} 天)...", flush=True)
    deadline = time.time() + WAIT_TIMEOUT
    while time.time() < deadline:
        if is_done(WAIT_LIVE):
            print("[wc] k20 已 done, 准备启动补扫", flush=True)
            return
        time.sleep(300)
    print("[wc] 等待超时(7天), 强制启动(假定编排器已结束/崩溃)", flush=True)


def run_scan(max_restarts=300, timeout=86400):
    args = [PY, str(SCRIPT), "--k", str(FIXED_K), "--n", str(N),
            "--conn-w", CONN_LEVELS, "--benchmark", str(BENCH),
            "--temperature", "0.0", "--live", LIVE, "--out", str(OUT)]
    logf = OUT / f"wc_k{FIXED_K}.log"
    for attempt in range(max_restarts):
        # Ollama 探活 (down 时持续等待, 不消耗 restart 次数, 抗休眠带停)
        if not ollama_ok():
            print(f"[wc] Ollama 暂不可用, 等待 60s 重试 (attempt {attempt+1})", flush=True)
            time.sleep(60)
            continue
        print(f"[wc] launch attempt {attempt+1}/{max_restarts}", flush=True)
        try:
            with open(logf, "a", encoding="utf-8") as lf:
                rc = subprocess.run(
                    args, env={**os.environ, "PYTHONUTF8": "1"},
                    stdout=lf, stderr=subprocess.STDOUT, timeout=timeout,
                ).returncode
        except subprocess.TimeoutExpired:
            print(f"[wc] 超时(>24h单轮), 视为被回收, 重启续跑", flush=True)
            rc = -9
        except Exception as e:
            print(f"[wc] 异常 {e}", flush=True)
            rc = -1
        if is_done(LIVE):
            print("[wc] DONE (status=done)", flush=True)
            return True
        print(f"[wc] 未 done (rc={rc}), 3s 后重启", flush=True)
        time.sleep(3)
    print("[wc] FAILED after restarts", flush=True)
    return False


def report():
    p = OUT / LIVE
    if not p.exists():
        print("[wc] live 不存在, 无法出报告")
        return
    d = json.loads(p.read_text(encoding="utf-8"))
    coll = d.get("collective_acc") or {}
    points = d.get("points") or []
    best = d.get("best_single")
    c0 = d.get("committee0")
    levels = [float(x) for x in CONN_LEVELS.split(",")]
    table = []
    for cw in levels:
        key = f"cw{cw:.2f}"
        cv = coll.get(key)
        row = next((r for r in points if abs(r.get("conn_w", -1) - cw) < 1e-6), None)
        g = row.get("G") if row else None
        table.append((cw, cv, g))

    # ---- 画图 ----
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        xs = [t[0] for t in table if t[1] is not None]
        ys = [t[1] for t in table if t[1] is not None]
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.plot(xs, ys, "o-", color="#1f77b4", lw=2, label="集体 M(Ẇ) 协作合成")
        if best is not None:
            ax.axhline(best, color="red", ls="--", lw=1.5, label=f"最强单体={best:.3f}")
        if c0 is not None:
            ax.axhline(c0, color="gray", ls=":", lw=1.2, label=f"纯投票(comm0)={c0:.3f}")
        ax.axvspan(0.45, 0.62, color="green", alpha=0.15, label="预言 Wc≈0.45-0.62")
        ax.set_xlabel("Ẇ (conn_w, 跨层连接强度)")
        ax.set_ylabel("集体准确率 M")
        ax.set_title(f"格式塔方程 M(Ẇ) @ k={FIXED_K} — 钉 Wc 峰位")
        ax.set_ylim(0.4, 1.0)
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(str(OUT / f"wc_scan_k{FIXED_K}.png"), dpi=120)
        print(f"[wc] 图已存 {OUT/'wc_scan_k{FIXED_K}.png'}", flush=True)
    except Exception as e:
        print(f"[wc] 画图失败(非致命): {e}", flush=True)

    # ---- md 摘要 ----
    opt = (d.get("superlinear") or {}).get("opt_conn_w")
    cmax = (d.get("superlinear") or {}).get("collective_max")
    beats = (cmax is not None and best is not None and cmax > best)
    lines = [f"# Wc 补扫报告 (固定 k={FIXED_K}, 扫 Ẇ 多档)",
             f"- 基准: {BENCH.name}  N={N}  temp=0",
             f"- 最强单体 best_single = {best}    委员会0(纯L3投票) = {c0}",
             f"- 最优 Ẇ = {opt}    峰值集体 = {cmax}    beats_best = {beats}",
             f"- 各 Ẇ 档均值见下表 (n={N} 每档独立)",
             "",
             "## 各 Ẇ 档结果",
             "| Ẇ(conn_w) | 集体 M | G = M − comm0 |",
             "|---|---|---|"]
    for cw, cv, g in table:
        lines.append(f"| {cw:.2f} | {cv if cv is not None else '—'} | {('+' + format(g, '.3f')) if g is not None else '—'} |")
    lines += ["",
              "## 判定 (对应方程 M(W)=0.5+0.25·(W/Wc)·e^(1−W/Wc))",
              "- 若 M(Ẇ) 在 Ẇ≈0.45–0.62 出现**内峰**、且 Ẇ=1.0 较峰位**回落** → 支持方程 Wc 预言 (有界单峰 kernel 真机成立)。",
              "- 若 M(Ẇ) 单调升至 Ẇ=1.0 仍不降 → 该操作化下 Wc>1.0 或 W 需 k×Ẇ 复合, 须修正论文主张。",
              "- 若 Ẇ=0 显著低于 Ẇ>0 → 协作合成机制有效 (对比纯投票 comm0 基线, 证伪'只是投票')。",
              "",
              "## 注意",
              "- 本补扫固定 k=10 (Condorcet 征募规模), 仅变 Ẇ 维度; 与原 '固定 Ẇ=1 扫 k' 互补。",
              "- 方程 M(W) 的 W 在此操作化为 conn_w (跨层连接强度); k 为固定调控参数。"]
    (OUT / f"wc_scan_report_k{FIXED_K}.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"[wc] 报告已存 {OUT/'wc_scan_report_k{FIXED_K}.md'}", flush=True)


def main():
    global OUT, BENCH, PY, SCRIPT, LOCK
    ap = argparse.ArgumentParser(description="格式塔方程 Wc 补扫编排器")
    ap.add_argument("--out", default=str(OUT), help="输出目录(默认仓库内 results/live)")
    ap.add_argument("--bench", default=str(BENCH), help="主基准 jsonl 路径")
    ap.add_argument("--py", default=PY, help="python 解释器路径(默认 sys.executable)")
    args = ap.parse_args()
    OUT = Path(args.out)
    BENCH = Path(args.bench)
    PY = args.py
    SCRIPT = HERE / "verify_stage2.py"
    LOCK = OUT / "wc_scan.lock"
    acquire_lock()
    try:
        wait_k20_done()
        time.sleep(60)  # 让编排器完全退出, 释放 Ollama 客户端
        ok = run_scan()
        if ok:
            report()
        else:
            print("[wc] 扫描失败, 未出报告", flush=True)
    finally:
        try:
            if LOCK.exists():
                LOCK.unlink()
        except Exception:
            pass


if __name__ == "__main__":
    main()
