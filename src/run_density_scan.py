#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
格式塔方程 —— 密度扫描编排器 (真机定位 Wc 峰位)
================================================
目的:
  现有数据只到 k=7, 方程峰位 Wc≈0.45-0.62 仅靠友人仿真 + 主基准 k5>k7 拐点佐证,
  尚未真机定位。本脚本扫 L3 独立专家数 k = [8,10,12,15,20] (k 增大 -> 连接密度 W 提高,
  对应 Condorcet 征募更多独立专家), 每个 k 跑主基准 N=500, temp=0, conn_w=1.0,
  输出 collective_acc / G, 拼出 M(W) vs k 曲线, 真机确认:
    (1) 峰值集体准确率是否确在 k≈5-6 (即 Wc≈0.45-0.62);
    (2) 过密 (大 k) 是否回落 (验证方程"过密回落"预言 + 非单调相变签名)。

设计 (同 run_light_repro.py):
  - 串行执行 (本机 CPU 推理, Ollama 并发<=2 客户端, 并行会互相饿死)
  - 前置等待: 必须等现有复现 (E3_k5_repro + subset_condC) 全部 done, 否则抢 Ollama
  - Ollama 探活前置
  - 子进程自带题级断点续跑; 单轮超时长 (大 k 在 CPU 极慢, k=20 可能 ~20-24h)
  - 各 k 独立 --live 文件名隔离
结果写 OUT/density_scan_summary.json
"""
import json, subprocess, sys, time, os, urllib.request, argparse
from pathlib import Path

# 仓库根 = 本脚本上级目录 (src/ 的父目录)
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCRIPT = HERE / "verify_stage2.py"                       # 与编排器同目录
BENCH = ROOT / "data" / "mcq_medium_clean.jsonl"        # 主基准 clean 500, 与 k3/k5/k7 同基准可比
OUT = ROOT / "results" / "live"                         # 默认输出到仓库内, 可复现不依赖本机路径
PY = sys.executable                                      # 用当前 python 解释器(无需硬编码路径)

DENSITY_KS = [8, 10, 12, 15, 20]
N = 500

REPLICATES = []
for k in DENSITY_KS:
    live = f"stage2_density_k{k}.json"
    REPLICATES.append({
        "name": f"density_k{k}",
        "live": live,
        "args": ["--k", str(k), "--n", str(N), "--conn-w", "1.0",
                 "--benchmark", str(BENCH), "--temperature", "0.0",
                 "--live", live],
        "note": f"密度扫描 k={k} (N={N}, temp=0) -> 真机定位 Wc / 过密回落",
    })

PRIOR_LIVES = ["e3_k5_repro.json", "stage2_subset_condC.json"]  # 对齐 E3 重跑 live 名(验证通过后重跑)


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


def is_done(live):
    p = OUT / live
    if not p.exists():
        return False
    try:
        return json.loads(p.read_text(encoding="utf-8")).get("status") == "done"
    except Exception:
        return False


def run_one(spec, max_restarts=60, timeout=86400):
    args = [PY, str(SCRIPT)] + spec["args"] + ["--out", str(OUT)]
    logf = OUT / f"density_{spec['name']}.log"
    if not ollama_ok():
        print(f"[{spec['name']}] Ollama 探活失败(>5min), 中止该扫描", flush=True)
        return False
    for attempt in range(max_restarts):
        print(f"[{spec['name']}] launch attempt {attempt+1}/{max_restarts}", flush=True)
        try:
            with open(logf, "a", encoding="utf-8") as lf:
                rc = subprocess.run(
                    args, env={**os.environ, "PYTHONUTF8": "1"},
                    stdout=lf, stderr=subprocess.STDOUT, timeout=timeout,
                ).returncode
        except subprocess.TimeoutExpired:
            print(f"[{spec['name']}] 超时(>{timeout//3600}h单轮), 视为被回收, 重启(题级断点续跑)", flush=True)
            rc = -9
        except Exception as e:
            print(f"[{spec['name']}] 异常 {e}", flush=True)
            rc = -1
        if is_done(spec["live"]):
            print(f"[{spec['name']}] DONE (status=done)", flush=True)
            return True
        print(f"[{spec['name']}] 未 done (rc={rc}), 3s 后重启", flush=True)
        time.sleep(3)
    print(f"[{spec['name']}] FAILED after {max_restarts} restarts", flush=True)
    return False


def wait_prior():
    """等待现有复现 (E3_k5_repro + subset_condC) 全部 done, 否则抢 Ollama 互相饿死。"""
    deadline = time.time() + 24 * 3600
    while time.time() < deadline:
        done = [is_done(l) for l in PRIOR_LIVES]
        if all(done):
            print("[density] 现有复现全部 done, 开始密度扫描", flush=True)
            return
        print(f"[density] 等待现有复现... {dict(zip(PRIOR_LIVES, done))}", flush=True)
        time.sleep(300)
    print("[density] 等待超时(24h), 强制开始(假定现有复现已结束/崩溃, 无活跃进程抢 Ollama)", flush=True)


def main():
    global OUT, BENCH, PY, SCRIPT
    ap = argparse.ArgumentParser(description="格式塔方程密度扫描编排器")
    ap.add_argument("--out", default=str(OUT), help="输出目录(默认仓库内 results/live)")
    ap.add_argument("--bench", default=str(BENCH), help="主基准 jsonl 路径")
    ap.add_argument("--py", default=PY, help="python 解释器路径(默认 sys.executable)")
    args = ap.parse_args()
    OUT = Path(args.out)
    BENCH = Path(args.bench)
    PY = args.py
    SCRIPT = HERE / "verify_stage2.py"
    if not ollama_ok():
        print("[density] Ollama 探活失败, 中止", flush=True)
        sys.exit(1)
    wait_prior()
    summary = {}
    for spec in REPLICATES:
        if is_done(spec["live"]):
            print(f"[{spec['name']}] 已完成, 跳过", flush=True)
        else:
            print(f"[density] >>> 开始 {spec['name']}: {spec['note']}", flush=True)
            run_one(spec, max_restarts=60, timeout=86400)
        p = OUT / spec["live"]
        if p.exists():
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
                coll = (d.get("collective_acc") or {}).get("cw1.00")
                best = d.get("best_single")
                g = (d.get("points") or {}).get("G")
                summary[spec["name"]] = {"k": int(spec["args"][1]),
                                          "collective": coll, "best_single": best, "G": g}
            except Exception as e:
                print(f"[density] 读 {spec['live']} 失败: {e}", flush=True)
    summ_path = OUT / "density_scan_summary.json"
    summ_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print("[density] ===== 密度扫描完成, 汇总 =====", flush=True)
    for name, v in summary.items():
        print(f"   {name}: k={v['k']} collective={v['collective']} best_single={v['best_single']} G={v['G']}", flush=True)
    print(f"[density] 汇总已写 -> {summ_path}", flush=True)


if __name__ == "__main__":
    main()
