#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
N=100 主复现显著性检验器 (导师整改②: N太小导致beats_best不显著)
==============================================================
读取 verify_stage2 落盘的 live json (含 committee0 / collective_acc / best_single / n_questions),
对每个 W 档做两比例 z 检验:
  - 集体 vs 弱投票基线(committee0): 检验 Sigma_si 架构合成增益是否显著
  - 集体 vs 最强单模型(best_single): 检验 beats_best 是否显著
显著性水平 alpha=0.05。

注意: 此处用两比例 z 检验(把集体与基线视为同 n 的独立样本),
属近似(严格应为配对 McNemar, 需逐题对错配对, 当前 live json 未存逐题明细)。
若 p<0.05 即标记显著。
"""
import sys, json, math

def phi(z):
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))

def ztest_ind(p1, n1, p2, n2):
    """两比例 z 检验 (双侧), 返回 (z, p, se_percent)."""
    se = math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    if se == 0:
        return 0.0, 1.0, 0.0
    z = (p1 - p2) / se
    p = 2 * (1 - phi(abs(z)))
    return z, p, se * 100

def main(path):
    d = json.load(open(path, encoding="utf-8"))
    base = d.get("committee0")
    best = d.get("best_single")
    N = d.get("n_questions") or len(d.get("node_acc", []) and [])
    ca = d.get("collective_acc", {})
    print(f"文件: {path}")
    print(f"n_questions = {N}")
    print(f"弱投票基线 committee0 = {base}")
    print(f"最强单模型 best_single = {best}")
    print(f"node_acc(各模型solo) = {d.get('node_acc')}")
    print("-" * 70)
    report = {"file": path, "N": N, "baseline": base, "best_single": best, "tiers": {}}
    for key in ["cw0.00", "cw0.50", "cw1.00", "cw1.0"]:
        v = ca.get(key)
        if v is None:
            continue
        z1, p1, se1 = ztest_ind(v, N, base, N)
        z2, p2, se2 = ztest_ind(v, N, best, N)
        g = round(v - base, 4)
        sig_base = "显著*" if p1 < 0.05 else "不显著"
        sig_best = "显著*" if p2 < 0.05 else "不显著"
        print(f"[{key}] 集体={v*100:.1f}%  G(base)=+{g*100:.1f}pt")
        print(f"    vs 基线: z={z1:.2f} p={p1:.4f} SE={se1:.1f}pt -> {sig_base}")
        print(f"    vs 最强单体: z={z2:.2f} p={p2:.4f} SE={se2:.1f}pt -> {sig_best}")
        report["tiers"][key] = {
            "collective": v, "G_vs_base": g,
            "z_vs_base": round(z1, 3), "p_vs_base": round(p1, 4), "sig_vs_base": p1 < 0.05,
            "z_vs_best": round(z2, 3), "p_vs_best": round(p2, 4), "sig_vs_best": p2 < 0.05,
        }
    # 总结论
    sb = any(t["sig_vs_base"] for t in report["tiers"].values())
    bb = any(t["sig_vs_best"] for t in report["tiers"].values())
    print("-" * 70)
    print(f"Sigma_si(架构合成>弱基线) 显著: {sb}")
    print(f"beats_best(集体>最强单体) 显著: {bb}")
    report["conclusion"] = {"sigma_si_significant": sb, "beats_best_significant": bb}
    out = path.replace(".json", "_sig.json")
    json.dump(report, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"报告 -> {out}")
    return report

if __name__ == "__main__":
    p = sys.argv[1] if len(sys.argv) > 1 else "stage2_rep1_live.json"
    main(p)
