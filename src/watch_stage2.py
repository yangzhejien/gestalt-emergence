#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stage 2 守护脚本：自动检测 verify_stage2 进程是否存活；
若被环境回收则自动重启；新出一档 conn_w 集体结果则写通知日志。
用法: python watch_stage2.py  (后台运行)
"""
import subprocess, time, json, os, sys

LIVE = "C:/Users/11409/WorkBuddy/2026-07-28-21-49-24/gestalt_live/stage2_live.json"
NOTIFY = "C:/Users/11409/WorkBuddy/2026-07-28-21-49-24/gestalt_live/stage2_notify.log"
START_CMD = r'cd /d D:\方程验证 && PYTHONUTF8=1 C:\Users\11409\.workbuddy\binaries\python\versions\3.13.12\python.exe "D:/方程验证/scripts/verify_stage2.py" --conn-w 0.0,0.5,1.0 --benchmark "D:/方程验证/benchmark/mcq_medium.jsonl" --n 30 --live stage2_live.json'

def log(msg):
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] {msg}\n"
    with open(NOTIFY, "a", encoding="utf-8") as f:
        f.write(line)
    print(line, end="")

def find_verify_pids():
    ps = (r'Get-CimInstance Win32_Process -Filter "Name=\'python.exe\'" | '
          r'Where-Object { $_.CommandLine -like \'*verify_stage2*\' } | '
          r'Select-Object -ExpandProperty ProcessId')
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                             capture_output=True, text=True, timeout=30).stdout
        return [int(x.strip()) for x in out.split() if x.strip().isdigit()]
    except Exception as e:
        return []

def start_verify():
    subprocess.Popen(START_CMD, shell=True)

def read_live():
    try:
        with open(LIVE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def main():
    log("WATCH START: 守护 Stage2 验证进程")
    notified = set()
    restart_count = 0
    while True:
        d = read_live()
        status = d.get("status")
        # 出结果通知
        for p in (d.get("points") or []):
            cw = p.get("conn_w")
            if cw not in notified:
                notified.add(cw)
                log(f"NEW conn_w={cw}  collective={p.get('collective')}  G={p.get('G')}  beats_best={'YES' if (p.get('collective') and d.get('best_single') and p['collective'] > d['best_single']) else 'no'}")
        if status == "done":
            log("DONE -> 全部完成, 终判: " + json.dumps(d.get("fit") or {}, ensure_ascii=False))
            break
        pids = find_verify_pids()
        if not pids:
            if status == "error":
                log("ERROR detected in live, restarting...")
            else:
                log("VERIFY DEAD (reclaimed), restarting...")
            restart_count += 1
            if restart_count > 12:
                log("RESTART LIMIT reached, stop watching. 请人工检查.")
                break
            start_verify()
            time.sleep(12)
            continue
        time.sleep(25)

if __name__ == "__main__":
    main()
