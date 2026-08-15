#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
格式塔复现 —— 监测镜像同步器
================================
编排器 replicate_stage2.py 顺序跑多个复现, 每个复现写入独立 live 文件
(stage2_rep1/2/3_live.json)。本同步器读取 replicate_state.json 的当前 idx,
把"正在跑的那个复现"live 文件每 2s 镜像到固定 replication_monitor.json,
供看板(8002)稳定读取, 用户无需在多个窗口间切换。
"""
import json, time, shutil, sys
from pathlib import Path

OUT = Path(r"C:/Users/11409/WorkBuddy/2026-07-28-21-49-24/gestalt_live")
STATE = OUT / "replicate_state.json"
MON = OUT / "replication_monitor.json"
REP_LIVES = ["stage2_rep1_live.json", "stage2_rep2_live.json", "stage2_rep3_live.json"]


def current_idx():
    try:
        s = json.loads(STATE.read_text(encoding="utf-8"))
        return int(s.get("idx", 0))
    except Exception:
        return 0


def main():
    print("[monitor_sync] 启动, 每2s镜像当前复现 live -> replication_monitor.json", flush=True)
    last = -1
    while True:
        idx = current_idx()
        if idx != last:
            print(f"[monitor_sync] 当前复现 idx={idx} ({REP_LIVES[idx] if 0 <= idx < len(REP_LIVES) else 'n/a'})", flush=True)
            last = idx
        if 0 <= idx < len(REP_LIVES):
            src = OUT / REP_LIVES[idx]
            if src.exists():
                try:
                    shutil.copy2(src, MON)
                except Exception as e:
                    sys.stderr.write(f"[monitor_sync copy fail] {e}\n")
        time.sleep(2)


if __name__ == "__main__":
    main()
