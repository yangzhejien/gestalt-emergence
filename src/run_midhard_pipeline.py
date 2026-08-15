#!/usr/bin/env python3
# run_midhard_pipeline.py — 单实例 pipeline: 生成中高难度基准 -> 探针核验三层难度带
# ─────────────────────────────────────────────────────────────────
# 单实例保护用 **O_EXCL 原子文件锁**: os.open(O_CREAT|O_EXCL) 在 Windows 上是原子的,
# 多个并发启动时只有一个能成功创建锁文件, 其余必然 FileExistsError 后直接退出 —— 彻底
# 消除 run_in_background 并发竞态。锁残留由外部(启动前 PowerShell 清场)删除。
# 用法: python run_midhard_pipeline.py   (建议用 run_in_background 托管)
# ─────────────────────────────────────────────────────────────────
import sys, os, json, time, subprocess, ctypes
PY = r"C:\Users\11409\.workbuddy\binaries\python\versions\3.13.12\python.exe"
ROOT = r"D:\方程验证"
LOCK = os.path.join(ROOT, "benchmark", "midhard_pipeline.lock")
LIVE = r"C:\Users\11409\WorkBuddy\2026-07-28-21-49-24\gestalt_live\midhard_live.json"
TARGET = 250  # 扩量: 给 n=50 三档密度扫描供足题库(每拓扑需 n=50, 多轮冗余)

def _pid_alive(pid):
    """可靠探活。Windows 用 OpenProcess(QUERY_LIMITED_INFORMATION): 拿到句柄=活, NULL=死。
    坑: 本机 os.kill(死pid,0) 抛 OSError[WinError 87] 而非 ProcessLookupError, 直用 os.kill
    会把死 pid 误判成"活着" -> 自愈合失效。故 Windows 走 OpenProcess, 不依赖 errno 误解。"""
    try:
        if sys.platform.startswith("win"):
            h = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)  # 0x1000=QUERY_LIMITED_INFO
            if h:
                ctypes.windll.kernel32.CloseHandle(h)
                return True
            return False
        else:
            os.kill(pid, 0)
            return True
    except Exception:
        return False

def acquire_single_instance():
    """原子获取单实例锁(O_EXCL). 返回 True=获得锁(继续), False=锁被活进程占用(退出).
    若锁指向的 pid 已死(僵尸锁, 常见于进程被外部 kill 而 finally 未跑), 自动清理后重试一次,
    避免"残留锁永久挡住重启"的坑."""
    try:
        fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, (str(os.getpid()) + "\n").encode())
        os.close(fd)
        return True
    except FileExistsError:
        try:
            cur = int((open(LOCK, encoding="utf-8").read().strip() or "0"))
            if cur and not _pid_alive(cur):
                os.remove(LOCK)
                fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, (str(os.getpid()) + "\n").encode())
                os.close(fd)
                print(f"[pipeline] 发现僵尸锁(pid={cur}已死), 已清理并接管", flush=True)
                return True
        except Exception:
            pass
        return False
    except Exception:
        return False

def write_live(d):
    try:
        tmp = LIVE + ".tmp"
        open(tmp, "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=False))
        os.replace(tmp, LIVE)
    except Exception:
        pass

def count_pool():
    p = os.path.join(ROOT, "benchmark", "mcq_midhard_pool.jsonl")
    if not os.path.exists(p):
        return 0
    return sum(1 for l in open(p, encoding="utf-8") if l.strip())

def main():
    if not acquire_single_instance():
        print("[pipeline] 锁已存在, 退出(防多副本踩踏)", flush=True)
        sys.exit(0)
    try:
        # ---- 生成阶段(循环直至达标; gen 自身也有断点续跑+attempts 上限) ----
        while count_pool() < TARGET:
            n = count_pool()
            write_live({"status": "running", "phase": "gen-midhard",
                        "progress": f"生成中 {n}/{TARGET}", "updated_at": time.strftime("%H:%M:%S")})
            rc = subprocess.run([PY, "scripts/gen_midhard_benchmark.py", "--target", str(TARGET),
                                 "--live", str(LIVE)],
                                cwd=ROOT).returncode
            print(f"[pipeline] gen 退出 rc={rc}, 池={count_pool()}", flush=True)
            if count_pool() >= TARGET:
                break
            time.sleep(2)
        # ---- 探针阶段(题库已扩大, 删旧 ckpt 防错位; supervisor 循环防崩溃中断) ----
        old_ckpt = os.path.join(ROOT, "benchmark", "mcq_midhard_probe.ckpt.json")
        if os.path.exists(old_ckpt):
            os.remove(old_ckpt); print("[pipeline] 已删旧探针 ckpt(题库已扩大)", flush=True)
        probe_json = os.path.join(ROOT, "benchmark", "mcq_midhard_probe.json")
        max_retries = 5
        for attempt in range(1, max_retries + 1):
            write_live({"status": "running", "phase": "probe-start",
                        "progress": f"生成完成, 启动探针核验三层难度带(第{attempt}次)", "updated_at": time.strftime("%H:%M:%S")})
            rc = subprocess.run([PY, "scripts/probe_hard.py",
                                 "--pool", "mcq_midhard_pool.jsonl",
                                 "--out-clean", "mcq_midhard_clean.jsonl",
                                 "--out-probe", "mcq_midhard_probe.json",
                                 "--live", "midhard_live.json",
                                 "--target-7b-lo", "0.60",
                                 "--target-7b-hi", "0.80",
                                 "--floor-3b", "0.25",
                                 "--floor-15b", "0.30",
                                 "--sample-7b", "100"], cwd=ROOT).returncode
            print(f"[pipeline] probe 退出 rc={rc} attempt={attempt}", flush=True)
            if os.path.exists(probe_json):
                break
            print("[pipeline] 探针未完成, 2s 后续跑(续断点)", flush=True)
            time.sleep(2)
        probe_json = os.path.join(ROOT, "benchmark", "mcq_midhard_probe.json")
        if os.path.exists(probe_json):
            res = json.load(open(probe_json, encoding="utf-8"))
            write_live({"status": "done", "phase": "midhard-final",
                        "progress": f"完成: 7B={res.get('acc_7b')} 3B={res.get('acc_3b')} 1.5B={res.get('acc_15b_sample')} band_ok={res.get('band_ok')}",
                        "band_ok": res.get("band_ok"), "floor_3b_ok": res.get("floor_3b_ok"),
                        "floor_15b_ok": res.get("floor_15b_ok"), "updated_at": time.strftime("%H:%M:%S")})
    finally:
        try:
            if os.path.exists(LOCK):
                os.remove(LOCK)
        except Exception:
            pass

if __name__ == "__main__":
    main()
