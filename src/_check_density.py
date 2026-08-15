import json, glob, os
print("=== 密度扫描进度 (live) ===")
for f in sorted(glob.glob('/c/Users/11409/WorkBuddy/2026-07-28-21-49-24/gestalt_live/stage2_density_k*.json')):
    try:
        d = json.load(open(f))
    except Exception as e:
        print(os.path.basename(f), "解析中(写入半截):", str(e)[:40])
        continue
    k = d.get('k')
    st = d.get('status')
    coll = d.get('collective') or (d.get('collective_acc') or {}).get('cw1.00')
    bs = d.get('best_single')
    print(f"k={k:>2} | status={st:<8} | collective={coll} | best_single={bs}")
print()
print("=== 后台密度进程 ===")
import subprocess
r = subprocess.run("ps -ef | grep -iE 'density|monitor' | grep -v grep | head -3", shell=True, capture_output=True, text=True)
print(r.stdout.strip() or "(无匹配)")
