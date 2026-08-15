# -*- coding: utf-8 -*-
""" streamlined 对照实验启动器(跳过已完成的 C-Eval k1/k3 冗余重跑)。
串行独占 Ollama(本机并发<=2), 依次: 翻译英文 -> 容量对照(L3=3B) -> 语言对照(英文C-Eval)。
日志: D:/方程验证/benchmark/_controls.log
"""
import subprocess, os, time

PY      = "C:/Users/11409/.workbuddy/binaries/python/versions/3.13.12/python.exe"
SCRIPT  = "D:/方程验证/scripts/verify_stage2.py"
GEN_EN  = "D:/方程验证/scripts/gen_ceval_en.py"
BENCH   = "D:/方程验证/benchmark/ceval_bandok_clean.jsonl"
BENCH_EN= "D:/方程验证/benchmark/ceval_en.jsonl"
CFG_CAP = "D:/方程验证/scripts/cfg_ceval_ctrl_cap.json"
LIVE_CAP  = "D:/方程验证/stage2_ceval_ctrl_cap_k1.json"
LIVE_LANG = "D:/方程验证/stage2_ceval_ctrl_lang_k1.json"
LOG     = "D:/方程验证/benchmark/_controls.log"

def log(m):
    t = time.strftime("%H:%M:%S")
    line = f"[controls] {t} {m}"
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line, flush=True)

if __name__ == "__main__":
    log("控制实验启动器开始(跳过已完成 C-Eval k1/k3)")
    # 1) 英文翻译(若不存在)
    if not os.path.exists(BENCH_EN):
        log("翻译 C-Eval -> 英文 (gen_ceval_en.py)")
        subprocess.run([PY, GEN_EN], check=True)
    else:
        log("ceval_en.jsonl 已存在, 跳过翻译")
    # 2) 容量对照: L3/agg/L2=3B, 主脑=7B, k=1
    log("启动 容量对照 L3=3B k=1 -> " + LIVE_CAP)
    subprocess.run([PY, SCRIPT, "--k", "1", "--benchmark", BENCH,
                    "--n", "200", "--conn-w", "1.0", "--seed", "20260810",
                    "--config", CFG_CAP, "--live", LIVE_CAP], check=True)
    log("容量对照完成 -> " + LIVE_CAP)
    # 3) 语言对照: 英文 C-Eval, 默认模型, k=1
    log("启动 语言对照 英文C-Eval 默认 k=1 -> " + LIVE_LANG)
    subprocess.run([PY, SCRIPT, "--k", "1", "--benchmark", BENCH_EN,
                    "--n", "200", "--conn-w", "1.0", "--seed", "20260810",
                    "--live", LIVE_LANG], check=True)
    log("语言对照完成 -> " + LIVE_LANG)
    log("ALL CONTROLS DONE")
