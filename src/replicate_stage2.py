#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
格式塔方程 Stage 2 —— 严格复现编排器
====================================
- 顺序跑多个复现(不同温度/随机性), 每个复现用 verify_stage2.py 完成
- verify_stage2.py 已具备题级断点续跑, 故本编排器在被环境回收后重启也能安全续跑
- 状态存 replicate_state.json, 重启时从断点继续, 不重跑已完成复现
"""
import json, subprocess, sys, time, os, urllib.request
from pathlib import Path

OUT = Path(r"C:/Users/11409/WorkBuddy/2026-07-28-21-49-24/gestalt_live")
ROOT = Path(r"D:/方程验证")
SCRIPT = ROOT / "scripts" / "verify_stage2.py"
BENCH = ROOT / "benchmark" / "mcq_medium.jsonl"
PY = r"C:/Users/11409/.workbuddy/binaries/python/versions/3.13.12/python.exe"
STATE = OUT / "replicate_state.json"

# 复现矩阵: 1 个 greedy(确定性复现确认) + 1 个 stochastic(temp=0.5, 采样分布复现).
# 配合已有 T3(n=30) 原始结果, 恰好构成 "原结果 + 2 次独立复现" 三连, 足以证明可复现.
# 注: 本机 Ollama 为 CPU 推理, 满 40 题 × 3 档 × 单次复现约需数小时, 故复现定为 2 次以控时长.
REPLICATES = [
    {"name": "rep1_greedy", "live": "stage2_rep1_live.json", "conn_w": "0.0,0.5,1.0", "temperature": 0.0, "n": 40,
     "note": "greedy 确定性复现(满40题)"},
    {"name": "rep2_temp05", "live": "stage2_rep2_live.json", "conn_w": "0.0,0.5,1.0", "temperature": 0.5, "n": 40,
     "note": "temp=0.5 随机复现(满40题)"},
]


def load_state():
    if STATE.exists():
        try:
            s = json.loads(STATE.read_text(encoding="utf-8"))
            if isinstance(s, dict) and "idx" in s and "status" in s:
                return s
        except Exception:
            pass
    return {"idx": 0, "status": {r["name"]: "pending" for r in REPLICATES}}


def save_state(s):
    try:
        STATE.write_text(json.dumps(s, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        sys.stderr.write(f"[state write fail] {e}\n")


def is_done(live_name):
    p = OUT / live_name
    if not p.exists():
        return False
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return d.get("status") == "done"
    except Exception:
        return False


def ollama_ok(url="http://127.0.0.1:11434/api/tags", tries=20, gap=15):
    """复现前探活 Ollama, 避免整档跑在已挂的 Ollama 上浪费数小时."""
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


def run_one(spec, max_restarts=10):
    args = [PY, str(SCRIPT), "--conn-w", spec["conn_w"], "--benchmark", str(BENCH),
            "--n", str(spec["n"]), "--live", spec["live"], "--temperature", str(spec["temperature"])]
    logf = OUT / f"rep_{spec['name']}.log"
    if not ollama_ok():
        print(f"[{spec['name']}] Ollama 探活失败(>5min), 中止该复现", flush=True)
        return False
    for attempt in range(max_restarts):
        print(f"[{spec['name']}] launch attempt {attempt+1}/{max_restarts}", flush=True)
        try:
            with open(logf, "a", encoding="utf-8") as lf:
                proc = subprocess.run(args, env={**os.environ, "PYTHONUTF8": "1"},
                                      stdout=lf, stderr=subprocess.STDOUT, timeout=7200)
                rc = proc.returncode
        except subprocess.TimeoutExpired:
            print(f"[{spec['name']}] 超时(>2h单轮), 视为被回收, 重启", flush=True)
            rc = -9
        except Exception as e:
            print(f"[{spec['name']}] 异常 {e}", flush=True)
            rc = -1
        if is_done(spec["live"]):
            print(f"[{spec['name']}] DONE (status=done)", flush=True)
            return True
        print(f"[{spec['name']}] 未 done (rc={rc}), 3s 后重启(题级断点续跑)", flush=True)
        time.sleep(3)
    print(f"[{spec['name']}] FAILED after {max_restarts} restarts", flush=True)
    return False


def main():
    s = load_state()
    print(f"[orchestrator] 从 idx={s['idx']} 继续; 状态={s['status']}", flush=True)
    while s["idx"] < len(REPLICATES):
        spec = REPLICATES[s["idx"]]
        if is_done(spec["live"]):
            s["status"][spec["name"]] = "done"
            s["idx"] += 1
            save_state(s)
            print(f"[{spec['name']}] 已完成, 跳过", flush=True)
            continue
        print(f"[orchestrator] >>> 开始 {spec['name']}: {spec['note']}", flush=True)
        ok = run_one(spec)
        s["status"][spec["name"]] = "done" if ok else "failed"
        if ok:
            s["idx"] += 1
        else:
            print("[orchestrator] 单复现失败, 中止(可重启编排器续跑)", flush=True)
            break
        save_state(s)
    print("[orchestrator] ALL REPLICATES PROCESSED", flush=True)


if __name__ == "__main__":
    main()
