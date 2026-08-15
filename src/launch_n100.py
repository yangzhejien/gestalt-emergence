#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
N=100 主复现启动器
=================
- 先写占位 live(供看板立即显示"等待7b")
- 轮询 ollama 直到原版 qwen2.5:7b 就位
- 调用 verify_stage2.py 跑 N=100 三档(greedy), 写 stage2_n100_live.json
- 带重试: 利用 verify 题级断点续跑, 进程被回收可自动重启
"""
import json, subprocess, sys, time, urllib.request
from pathlib import Path

OUT = Path(r"C:/Users/11409/WorkBuddy/2026-07-28-21-49-24/gestalt_live")
PY = r"C:/Users/11409/.workbuddy/binaries/python/versions/3.13.12/python.exe"
SCRIPT = r"D:/方程验证/scripts/verify_stage2.py"
BENCH = r"D:/方程验证/benchmark/mcq_medium.jsonl"
LIVE = OUT / "stage2_n100_live.json"

# 占位 live, 让看板立刻有东西可显示
placeholder = {
    "status": "init", "progress": "等待原版 qwen2.5:7b 拉取完成",
    "committee0": None, "collective_acc": {}, "node_acc": [],
    "updated_at": "waiting-7b",
}
LIVE.write_text(json.dumps(placeholder, ensure_ascii=False), encoding="utf-8")
print("[launcher] 占位 live 已写, 开始等待 7b...", flush=True)

# 等待原版 7b 就位 (最多 15 分钟)
for i in range(180):
    try:
        d = json.load(urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=5))
        if any("qwen2.5:7b" in m["name"] for m in d.get("models", [])):
            print("[launcher] qwen2.5:7b ready", flush=True)
            break
    except Exception:
        pass
    time.sleep(5)
else:
    print("[launcher] 7b 超时未就绪, 退出", flush=True)
    sys.exit(1)

# 跑 verify_stage2 N=100, 带重试(题级续跑)
args = [PY, SCRIPT, "--n", "100", "--benchmark", BENCH,
        "--conn-w", "0.0,0.5,1.0", "--temperature", "0.0",
        "--live", str(LIVE)]
log = OUT / "n100_run.log"
for attempt in range(6):
    print(f"[launcher] verify attempt {attempt+1}/6", flush=True)
    rc = subprocess.run(args, stdout=open(log, "a", encoding="utf-8"),
                        stderr=subprocess.STDOUT).returncode
    try:
        st = json.loads(LIVE.read_text(encoding="utf-8")).get("status")
    except Exception:
        st = None
    if st == "done":
        print("[launcher] N=100 主复现完成 (status=done)", flush=True)
        break
    print(f"[launcher] rc={rc} status={st}, 5s 后重试(题级续跑)", flush=True)
    time.sleep(5)
else:
    print("[launcher] 多次重试仍失败, 请检查 n100_run.log", flush=True)
