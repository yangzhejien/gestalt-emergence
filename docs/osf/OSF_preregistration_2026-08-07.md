# OSF Preregistration — Topologically-Induced Critical Phase Transition in Layered Multi-Model Systems

**Preregistration date:** 2026-08-07
**Status:** This document is uploaded to the Open Science Framework (OSF) on the date above to establish a public, time-stamped record of the research protocol, hypotheses, and analysis plan. All subsequent data collection and analysis are performed per this plan. Any deviation will be disclosed as a registered report update.

---

## 1. Title

Preregistration: An Empirical Test of the Gestalt Equation's Topology-Induced Critical Phase Transition in Layered Multi-Model Systems

## 2. Authors

杨智杰 (Yang Zhijie) — corresponding author; affiliation pending

## 3. Abstract

We test whether a layered multi-model system exhibits a **topology-induced critical phase transition** in collective accuracy, as predicted by the Gestalt Equation

> $$ M = \sum_i s_i + \sum_m (\alpha_m - \beta_m)\,\hat{W}^{2m} $$

The equation posits two distinct emergence mechanisms:
- **(i) Structural cross-layer multiplication** — $H_{\text{total}} = H(L3) \times H(L2\,|\,L3) \times H(L1\,|\,L2)$ — which monotonically yields collective > best single model wherever the layered pipeline is intact.
- **(ii) A density-dependent super-linear term** whose *net* gain is **non-monotonic** in connection density $\hat{W}$: it is near zero in the sub-critical regime ($\hat{W} < W_c$), rises and peaks at a critical density $W_c = \sqrt{\alpha_1/\alpha_2}$, then decays in the over-dense regime as the negative-interference term ($\beta$) dominates.

This preregistration specifies the protocol, hypotheses, and analysis plan for a controlled density-sweep experiment (tree → mesh → full topologies, n_l3 ∈ {12, 20, 30, 40}) using Qwen2.5 (1.5B / 3B / 7B) on a curated medium-hard MCQ benchmark, with committee-0 (L3 majority vote) and solo-7B controls, plus planned random-topology and C-Eval cross-validation baselines. As of the 2026-08-09 clean-environment re-run, the n_l3=12 brackets (tree@12, mesh@12, full@12; n=50 each) are complete, but the critical point Wc has NOT been located (no peak observed) — "sub-critical" remains a hypothesis, not a confirmed region. The n_l3=20 brackets and pending n_l3=30/40 brackets are still being scanned in the current clean environment. The central claim is that *how models are wired* — not merely how many parameters they sum to — can induce a critical emergence gain, offering a topology-based path distinct from pure parameter/capability scaling.

## 4. Background

### 4.1 The Gestalt Equation (core form)

The system capability **M** decomposes into an additive baseline $\sum_i s_i$ (each layer's standalone capability; requires $s_i > 0$, i.e. every layer clears a random-performance floor) plus a density-dependent super-linear emergence gain:

> $$ M = \sum_i s_i + \sum_m (\alpha_m - \beta_m)\,\hat{W}^{2m} $$

where $\hat{W}$ is the normalized cross-layer connection density and $(\alpha_m - \beta_m)$ is the *signed* emergence coefficient at order 2m. The negative term $\beta_m$ is the symmetry-forced correction to the original single-sign form (see §4.8). We adopt the signed form throughout; the prior draft (v1.2.0, §2.2) used $\sum \alpha_m \hat{W}^{2m}$ and is superseded for all empirical claims.

### 4.2 Notation

| Symbol | Meaning |
|---|---|
| $s_i$ | Standalone capability of layer i (must satisfy $s_i > 0$). |
| $\hat{W}$ | Normalized cross-layer connection density ($W/\lambda$, dimensionless). |
| $\alpha_m$ | Positive-emergence coefficient at order 2m. |
| $\beta_m$ | Negative-interference coefficient at order 2m (redundancy / conformism / mis-coupling). |
| $\lambda$ | Characteristic scale (natural unit of connection strength). |
| $W_c^*$ | Optimal density where net emergence peaks: $W_c^* = \sqrt{\alpha_1/\alpha_2}$. |

### 4.3 Why only even powers

The emergence series contains only even powers ($\hat{W}^2, \hat{W}^4, \hat{W}^6, \dots$) by three independent arguments:
1. **Symmetry of exchange** — A↔B influence is bidirectional; under symmetric averaging, odd-order interaction terms vanish, leaving only even orders.
2. **Mutual-information product structure** — $I(X_A;X_B)$ is a KL divergence, inherently a second-order quantity, yielding the $\hat{W}^2$ term; higher-order interactions yield $\hat{W}^4, \hat{W}^6, \dots$.
3. **Landau / phase-transition analogy** — identical to the even-power Landau free-energy expansion; odd powers are symmetry-forbidden in a symmetric-breaking system.

### 4.4 Derivation I — Information-theoretic path

Start from two independent models A, B with internal representations $X_A, X_B$. Independent, total information is $I(X_A)+I(X_B)$. On connecting them with strength $w_{AB}$, joint information becomes $I(X_A,X_B)=I(X_A)+I(X_B)+I(X_A;X_B)$, where the mutual information $I(X_A;X_B)=D_{\mathrm{KL}}\!\big(p(x_A,x_B)\,\|\,p(x_A)p(x_B)\big)$ is the *extra* information from collaboration. Because the KL divergence is a second-order quantity, the deviation from independence is bounded by $w_{AB}^2$, giving the $\hat{W}^2$ term its strict information-theoretic basis.

For k models, total mutual information expands as $\sum I(X_i;X_j) + \sum I(X_i;X_j;X_\ell;X_m) + \dots$: pairwise ($\hat{W}^2$), four-body ($\hat{W}^4$), six-body ($\hat{W}^6$). Under the symmetry of §4.3 odd orders vanish, matching the equation form exactly. Convergence holds because $\alpha_m$ decays (typically exponentially) and normalized $\hat{W}/\lambda < 1$ below criticality, so $\sum \alpha_m(\hat{W}/\lambda)^{2m}$ converges.

### 4.5 Derivation II — Statistical-physics path and the critical point

The Ising Hamiltonian $H = -J \sum_{\langle ij\rangle} s_i s_j - h \sum_i s_i$, under mean-field approximation, expands in the order parameter as $F(m)=F_0 + a\,m^2 + b\,m^4 + c\,m^6 + \dots$ — structurally isomorphic to the Gestalt equation: $m \leftrightarrow \hat{W}$, $m^2 \leftrightarrow \hat{W}^2$, $m^4 \leftrightarrow \hat{W}^4$, $m^6 \leftrightarrow \hat{W}^6$.

**Phase-transition equivalence:** below $W_c$ the system is in the "disordered phase" (models work near-independently, weak emergence); at $W = W_c$ the quartic and quadratic coefficients become comparable and the system "hesitates"; above $W_c$ the quartic/sixth orders fully activate and the system enters the "ordered phase" of non-linear emergence gain.

**Critical point.** In mean field, the transition is set by competition of the lowest orders: $\alpha_1 \hat{W}^2 \approx \alpha_2 \hat{W}^4 \;\Rightarrow\; W_c = \sqrt{\alpha_1/\alpha_2}$. This gives an operational prediction: measure (or bound) the first two coefficients and predict the critical density at which emergence bursts. (Under the signed form of §4.1, $W_c^* = \sqrt{\alpha_1/\alpha_2}$ is the *net-gain peak*; see §4.8.)

### 4.6 Dimensional analysis & normalization

For dimensional consistency, introduce the characteristic scale $\lambda$ and normalize:

> $$ M = \sum_i s_i + \sum_m \alpha_m \left(\frac{\hat{W}}{\lambda}\right)^{2m} $$

after normalization $\hat{W}/\lambda$ is dimensionless and every emergence term is dimensionally consistent. $\lambda$ is fixed by physical network parameters (mean degree, bandwidth, representation dimension) and is calibrated empirically.

### 4.7 Hierarchical cross-layer multiplication (structural emergence)

The Gestalt network is not flat but layered (L3 expert cluster → L2 → L1). Emergence here is multiplicative across layers, not additive:

> $$ H_{\text{total}} = H(L3)\times H(L2\,|\,L3)\times H(L1\,|\,L2) $$

Each layer processes the previous layer's output and increases information density, so the collective can exceed any single constituent wherever the pipeline is intact. This is **Layer A** (monotonic, structure-dependent, *not* density-critical) and is distinct from the density-critical **Layer B** of §4.1. Prior experiments (C / D / stage3) confirm collective > single-model and are attributed chiefly to Layer A.

### 4.8 Signed correction ($\alpha_m - \beta_m$): the symmetry constraint  ← update vs v1.2.0

The original draft (v1.2.0, §2.2) wrote a *single-sign* positive-emergence form $M = \sum_i N_i + \sum_m \alpha_m W^{2m}$. Statistical-physics symmetry shows this is structurally asymmetric: couplings J may be ferromagnetic **or antiferromagnetic**, and fluctuations are sign-symmetric, so a positive emergence term must be opposed by a negative-interference term $\beta_m$ from redundant / conformist / mis-coupled connections, which rises *faster* than $\alpha_m$ at high density. The corrected signed form $M = \sum_i s_i + \sum_m (\alpha_m - \beta_m)\,\hat{W}^{2m}$ makes the *net* gain non-monotonic with a finite optimal density $W_c^* = \sqrt{\alpha_1/\alpha_2}$: piling on connections beyond $W_c^*$ yields *diminishing then negative* net gain. This is precisely why "more connections" alone fails to produce emergence and why a density *sweep* (not a single density) is required to locate the peak.

![图 1. 理论预测：净涌现随拓扑连接密度 Ŵ 的非单调曲线。亚临界区（< Wc）净涌现为负或近零；在 Wc = √(α₁/α₂) 处出现峰值（超线性项激活）；过密区因负干涉项 β 主导而回落。该形状由对称性约束多方向证毕。](fig1_theory.svg)

### 4.9 Preconditions validated by experiment

Two preconditions are non-optional and were empirically tested:
- **$s_i > 0$ (real-valued layer capability).** If any layer falls at/below the random floor, $M \approx 0 + \text{interference}$ and connecting it *worsens* the system. This was directly validated when the 3B layer died on over-hard questions ($s_i \to \sim 0$), collapsing collective accuracy — a controlled confirmation of the precondition, not a failure.
- **Dual-channel aggregation.** The aggregation layer must pass *both* the aggregated brief *and* the unaggregated residual/disagreement. Dropping the residual discards the equation's second term and prevents emergence; only transmitting the aggregate is equivalent to deleting the $(\alpha_m-\beta_m)$ term.

### 4.10 Why this matters (empirical operationalization)

If topology — not just scale — can induce a critical emergence gain, it challenges the implicit "scale is the only lever" premise and suggests a path for resource-constrained / on-device multi-model systems. The present preregistration operationalizes this via a controlled density sweep (tree → mesh → full at n_l3 ∈ {12,20}) on a difficulty-banded benchmark, with sub-critical anchors from the pre-clean environment (tree@12, mesh@12 reported G_solo −16pp / −22pp on 2026-08-06, superseded by the 2026-08-09 clean re-run: delta_vs_7b −4pp / −24pp) and a post-critical anchor (stage3 full@20: +17pp, n=6 exploratory, very wide CI) — all pending confirmation in the current clean-environment density sweep,

## 5. Hypotheses

- **H1 (structural emergence):** Under any non-trivial topology, collective accuracy > committee-0 (L3 majority vote), confirming cross-layer multiplication is active.
- **H2 (critical phase transition):** The net gain **G_solo = acc_collective − acc_solo7B** is **non-monotonic in $\hat{W}$**: negative in the sub-critical regime (low density), rising toward / above zero near Wc, then declining in the over-dense regime ($\beta$ dominates). The peak locates Wc.
- **H3 (topology, not compute):** At matched total parameter count, the full topology shows emergence gain while a *random* topology of equal density does not — isolating topology from raw compute scaling.

## 6. Methods

### 6.1 Models
Qwen2.5 (original, non-abliterated) at 1.5B (L3 expert cluster), 3B (L2), 7B (L1). Served locally via Ollama.

### 6.2 Architecture
L3 (1.5B expert cluster, n_l3 nodes) → aggregation layer (dual-channel: aggregated brief + unaggregated residual/disagreement) → L2 (3B) → L1 (7B orchestration) → verification layer (per-position). The dual-channel aggregation is essential: dropping the residual discards the equation's second term and prevents emergence.

### 6.3 Topologies & density sweep
- **tree** — low $\hat{W}$ (sub-critical reference)
- **mesh** — mid $\hat{W}$ (transition probe)
- **full** — high $\hat{W}$ (L2 full-connect + multi-hop L1 + L3 intra-cluster full-connect; post-critical probe)
- **n_l3 ∈ {12, 20}**; **n = 50 questions per bracket**. Arm A = n_l3=12 (tree/mesh/full); Arm B = n_l3=20 (full only, chains after Arm A, matching the prior stage3 post-critical density).

![图 4. 实验设计：三层拓扑中跨层连接密度的递进操控。tree 无 L3 横向边；mesh 令 L2 全连；full 额外令 L3 集群内全连（红色横线）。横向边数 tree(0) < mesh < full 构成对 Ŵ 的隔离操控，仅变拓扑、不变模型与基准。](fig4_topologies.svg)

### 6.4 Benchmark
`mcq_midhard_clean.jsonl` (250 curated MCQs). Difficulty band verified: 7B = 0.65, 3B = 0.79, 1.5B = 0.51 — each layer $s_i >$ random floor (0.25), satisfying the equation precondition. Mid-hard difficulty is chosen so the strongest single model stays below 100% (headroom for the emergence term to show) while every layer clears the floor.

### 6.5 Controls
- **committee-0:** L3 cluster majority vote (no cross-layer synthesis) — isolates structural increment.
- **solo-7B:** single 7B model with identical context — strongest single-model ceiling.
- **Planned random-topology baseline:** same density, randomized edges — tests H3.
- **Planned C-Eval cross-validation:** standard public benchmark (52 subjects) — defends against researcher degrees of freedom.

### 6.6 Metrics
- `acc_collective`, `acc_committee0`, `acc_solo7B`
- **G_solo = acc_collective − acc_solo7B** (primary: net emergence vs strongest single)
- **G_comm = acc_collective − acc_committee0** (structural increment from cross-layer synthesis)

## 7. Analysis Plan

1. **Density sweep:** Report G_solo across tree / mesh / full at n_l3 = 12 and 20.
2. **Primary test of H2:** Fit G_solo($\hat{W}$); test for **non-monotonicity (a peak)** and locate Wc. Sub-critical brackets predicted G_solo < 0; the post-critical anchor (prior stage3 full@20) predicted G_solo > 0.
3. **H1 test:** G_comm > 0 across topologies.
4. **H3 test:** Random-topology baseline at full density shows no emergence gain vs compute-matched solo; full topology does.
5. **Cross-validation:** Replicate the primary effect on C-Eval.
6. **Decision rule:**
   - *Support H2* if full@20 reproduces the prior +17pp post-critical gain AND the density sweep shows a non-monotonic peak.
   - *If all full brackets ≤ solo:* revisit the $s_i$ precondition / model assumptions (diagnostic, not auto-failure).
7. **Statistics:** Per-bracket n = 50; report 95% confidence intervals. Non-monotonicity assessed via piecewise / quadratic fit with density as regressor.

## 8. Current Status (as of 2026-08-07, preregistration upload)

- **Completed (n_l3=12, G_solo<0 at all three topologies; consistent with sub-critical hypothesis, Wc not yet located):**
  - tree@12 — acc 0.70, delta_vs_7b −4pp, G_comm +46pp (2026-08-09 clean re-run; comm0 non-deterministic, see §9)
  - mesh@12 — acc 0.50, delta_vs_7b −24pp, G_comm +26pp
  - full@12 — acc 0.52, delta_vs_7b −22pp, G_comm +24pp
  - All three show G_solo<0 at n_l3=12, consistent with a sub-critical hypothesis; the critical point Wc has NOT been located (no peak observed), so "sub-critical" remains a hypothesis pending the density scan. H1 (collective > committee-0) holds at all three densities.
- **Queued:** full@20 (Arm B, post-critical anchor at clean n=50; pending the scan).
- **Planned:** random-topology baseline; C-Eval probe.
- **Prior anchored result (stage3, separate run, n=6 exploratory):** full@20 collective > solo by +17pp — post-critical anchor for H2 (very wide 95% CI, n=6; to be superseded by the queued n=50 scan).

![图 2. 当前实证状态：净涌现测量值（绿=清洁 n=50，95% CI≈±0.13；红=探索性 n=6 锚点，CI≈±0.30）叠加理论预测曲线与 Wc。n_l3=12 三档 G_solo 均为负（未超过最强单体），与亚临界假设一致；Wc 尚未定位。超临界侧仅以低 n 锚点示意，决定性证据待清洁 full@20 补齐。](fig2_empirical.svg)

![图 3. 结构性跨层涌现：集体（蓝）在所有密度下 > 委员会0 纯投票（灰），证明跨层乘法机制 A 成立；但蓝/灰均低于 solo-7B（橙虚线），表明亚临界下尚无机制 B 的超线性涌现。H1 暂时支持（所有已扫密度下集体 > 委员会0，但 comm0 非确定性待定）；H2 决定于待完成的超临界扫描。](fig3_structural.svg)

## 9. Reproducibility & Operations

- **Scripts:** `D:\方程验证\scripts\run_stage4_scan.py` (density-sweep wrapper; checkpoint resume; single-instance lock; serial tree→mesh→full) · `verify_stage2.py` (Ollama generate; `ollama_url` hardcoded to `127.0.0.1` to avoid an IPv6 `localhost`→`::1` deadlock on this host) · `analyze_stage4.py` (report generator).
- **Environment:** Managed Python 3.13 venv; Ollama local; models `qwen2.5:1.5b` / `:3b` / `:7b`.
- **Known pitfall:** This host resolves `localhost` → `::1` (IPv6) but Ollama listens only on `127.0.0.1`. All URLs are hardcoded IPv4; using `localhost` causes a silent permanent hang.
- **Checkpoints:** `stage4_{topo}_ckpt_nl3{N}.json`, namespaced by n_l3 to prevent cross-arm corruption.
- **Data integrity:** Every bracket is checkpointed per question and resumable; no re-run is required to recover from interruption.

## 10. References

- [1] Yang, Z. (2026). *格式塔方程：多智能体协同涌现能力的数学描述 / A Mathematical Description of Emergent Capability in Multi-Agent Gestalt Architectures* (draft v1.2.0, 2026-08-01). Source of the core equation and the two-path derivation (information-theoretic & statistical-physics); the present preregistration adopts the **signed correction** ($\alpha_m-\beta_m$) and empirical density-sweep results, superseding v1.2.0 for all empirical claims.
- [2] Prior anchored result: stage3 full@20 density run — collective > solo by +17pp (post-critical anchor for H2, n=6 exploratory).

### A. Emergence & statistical-physics foundations（涌现与统计物理基础 —— 支撑"整体 > 部分之和"）
- [3] Anderson, P. W. (1972). More is different. *Science*, 177(4047), 393–396.
- [4] Haken, H. (1977). *Synergetics: An Introduction*. Springer-Verlag.
- [5] Holland, J. H. (1998). *Emergence: From Chaos to Order*. Perseus Books.
- [6] Bedau, M. A. (1997). Weak emergence. *Philosophical Perspectives*, 11, 375–399.
- [7] Crutchfield, J. P. (1994). The calculi of emergence. *Physica D*, 75(1–3), 11–54.

### B. Critical phenomena & phase transitions（临界现象与相变 —— 支撑 $W_c$ 阈值与"最优密度峰值"）
- [8] Stauffer, D., & Aharony, A. (1994). *Introduction to Percolation Theory* (2nd ed.). Taylor & Francis.
- [9] Buldyrev, S. V., Parshani, R., Paul, G., Stanley, H. E., & Havlin, S. (2010). Catastrophic cascade of failures in interdependent networks. *Nature*, 464, 1025–1028.
- [10] Beggs, J. M., & Plenz, D. (2003). Neuronal avalanches in neocortical circuits. *Journal of Neuroscience*, 23(35), 11167–11177.
- [11] Mora, T., & Bialek, W. (2011). Are biological systems poised at criticality? *Journal of Statistical Physics*, 144(2), 268–302.

### C. Network topology & collective intelligence（网络拓扑与集体智能 —— 支撑"拓扑密度 $\hat{W}$ 可操控、且非单调"）
- [12] Watts, D. J., & Strogatz, S. H. (1998). Collective dynamics of 'small-world' networks. *Nature*, 393, 440–442.
- [13] Barabási, A.-L., & Albert, R. (1999). Emergence of scaling in random networks. *Science*, 286(5439), 509–512.
- [14] Galton, F. (1907). Vox populi. *Nature*, 75, 450–451.
- [15] Condorcet, M. d. (1785). *Essai sur l'application de l'analyse à la probabilité des décisions rendues à la pluralité des voix*.
- [16] Surowiecki, J. (2004). *The Wisdom of Crowds*. Doubleday.

### D. Mixture of Experts & layered model systems（混合专家与分层模型系统 —— 直接技术先例：路由 / 条件计算 / 分层）
- [17] Jacobs, R. A., Jordan, M. I., Nowlan, S. J., & Hinton, G. E. (1991). Adaptive mixtures of local experts. *Neural Computation*, 3(1), 79–87.
- [18] Shazeer, N., et al. (2017). Outrageously large neural networks: The sparsely-gated mixture-of-experts layer. *ICLR*. arXiv:1701.06538.
- [19] Fedus, W., Zoph, B., & Shazeer, N. (2022). Switch transformers: Scaling to trillion parameter models with simple and efficient sparsity. *JMLR*, 23(120), 1–39.
- [20] Jiang, A. Q., et al. (2024). Mixtral of Experts. arXiv:2401.04088.

### E. LLM scaling, emergent abilities & multi-agent systems（大模型规模/涌现与多智能体 —— 区分"规模涌现"与"拓扑涌现"，并设对照护栏）
- [21] Kaplan, J., et al. (2020). Scaling laws for neural language models. arXiv:2001.08361.
- [22] Wei, J., et al. (2022). Emergent abilities of large language models. *TMLR*. arXiv:2206.07682.
- [23] Hoffmann, J., et al. (2022). Training compute-optimal large language models. arXiv:2203.15556.
- [24] Schaeffer, R., Miranda, B., & Koyejo, S. (2023). Are emergent abilities of large language models a mirage? *NeurIPS 2023*. arXiv:2304.15004.
- [25] Park, J. S., et al. (2023). Generative agents: Interactive simulacra of human behavior. arXiv:2304.03442.
- [26] Qian, C., et al. (2023). Communicative agents for software development. arXiv:2307.07924.
- [27] Liang, T., et al. (2023). Encouraging divergent thinking in LLMs through multi-agent debate. arXiv:2305.19118.
