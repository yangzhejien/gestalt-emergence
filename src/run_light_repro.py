#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
格式塔方程 —— 轻量稳健性复现编排器
===================================
目标(用户 2026-08-11 选定 "轻量稳健性复现"):
  1) E3 k5 同配置重跑(原始模型 qwen2.5, N=500, temp=0) -> 验证原值 0.942 重现
     (条件C 已有 condC_clean_relive.json = 0.924 重现; 本步补齐 E3 的复现)
  2) 换样本子集 跑条件C(k=3, temp=0) -> 验证涌现非特定 500 题偶然
        —— 主基准 temp=0 + 答案代码算 => 模型输出确定性, 换 Ollama seed 无效;
           真正有效的稳健性维度是"换样本子集", 故(2)用 random.sample 抽 N=200 不同题.

设计:
  - 每个复现独立 --live 文件名隔离(避免覆盖原 stage2_E3_k5.json 等).
  - verify_stage2.py 自带题级断点续跑(tiers/<live_stem>_cw*.jsonl), 故本编排器被环境回收后重启可续.
  - Ollama 探活前置, 避免整档跑在已挂的 Ollama 上浪费数小时.
  - 串行执行(本机 CPU 推理, Ollama 并发<=2 客户端, 并行会互相饿死).
"""
import json, subprocess, sys, time, os, urllib.request, random
from pathlib import Path

OUT = Path(r"C:/Users/11409/WorkBuddy/2026-07-28-21-49-24/gestalt_live")
ROOT = Path(r"D:/方程验证")
SCRIPT = ROOT / "scripts" / "verify_stage2.py"
BENCH_FULL = ROOT / "benchmark" / "mcq_medium_clean.jsonl"   # ★修正: 必须用清洗版(原误用未清洗mcq_medium.jsonl导致11道坏题污染聚合, collective崩到0.498)
SUBSET_SEED = 20260811
SUBSET_N = 200
PY = r"C:/Users/11409/.workbuddy/binaries/python/versions/3.13.12/python.exe"
SUBSET_PATH = ROOT / "benchmark" / f"mcq_medium_sub200_s{SUBSET_SEED}.jsonl"

REPLICATES = [
    {
        "name": "E3_k5_repro",
        "live": "stage2_E3_k5_repro.json",
        "args": ["--k", "5", "--n", "500", "--conn-w", "1.0",
                 "--benchmark", str(BENCH_FULL), "--temperature", "0.0",
                 "--live", "stage2_E3_k5_repro.json"],
        "note": "E3 k5 同配置重跑(N=500, temp=0) -> 目标重现 0.942",
    },
    {
        "name": "subset_condC",
        "live": "stage2_subset_condC.json",
        "args": ["--k", "3", "--n", str(SUBSET_N), "--conn-w", "1.0",
                 "--benchmark", str(SUBSET_PATH), "--temperature", "0.0",
                 "--live", "stage2_subset_condC.json"],
        "note": f"换样本子集(N={SUBSET_N}, seed={SUBSET_SEED}) 条件C(k=3, temp=0) -> 验证非特定题集涌现",
    },
]


def gen_subset():
    if SUBSET_PATH.exists():
        print(f"[subset] 已存在 {SUBSET_PATH}, 跳过生成")
        return
    rows = [l for l in BENCH_FULL.read_text(encoding="utf-8").splitlines() if l.strip()]
    if len(rows) < SUBSET_N:
        print(f"[subset] 题数不足 {len(rows)} < {SUBSET_N}")
        sys.exit(1)
    random.seed(SUBSET_SEED)
    picked = random.sample(rows, SUBSET_N)
    SUBSET_PATH.write_text("\n".join(picked) + "\n", encoding="utf-8")
    print(f"[subset] 生成 {SUBSET_PATH} ({SUBSET_N} 题, seed={SUBSET_SEED})")


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


def run_one(spec, max_restarts=30):
    args = [PY, str(SCRIPT)] + spec["args"] + ["--out", str(OUT)]
    logf = OUT / f"repro_{spec['name']}.log"
    if not ollama_ok():
        print(f"[{spec['name']}] Ollama 探活失败(>5min), 中止该复现", flush=True)
        return False
    for attempt in range(max_restarts):
        print(f"[{spec['name']}] launch attempt {attempt+1}/{max_restarts}", flush=True)
        try:
            with open(logf, "a", encoding="utf-8") as lf:
                rc = subprocess.run(
                    args, env={**os.environ, "PYTHONUTF8": "1"},
                    stdout=lf, stderr=subprocess.STDOUT, timeout=18000,
                ).returncode
        except subprocess.TimeoutExpired:
            print(f"[{spec['name']}] 超时(>5h单轮), 视为被回收, 重启(题级断点续跑)", flush=True)
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


def main():
    gen_subset()
    for spec in REPLICATES:
        if is_done(spec["live"]):
            print(f"[{spec['name']}] 已完成, 跳过", flush=True)
            continue
        print(f"[orchestrator] >>> 开始 {spec['name']}: {spec['note']}", flush=True)
        if not run_one(spec):
            print(f"[orchestrator] {spec['name']} 失败, 中止(可重启编排器续跑)", flush=True)
            break
    print("[orchestrator] ALL REPLICATES PROCESSED", flush=True)


if __name__ == "__main__":
    main()
