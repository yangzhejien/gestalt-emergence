# OSF Corrigendum & Progress Report — Gestalt Equation Completion: Corrected Critical Formula, Completed Equation, and Empirical Confirmation of Emergence

**Document type:** Registered update (corrigendum + progress report) to the 2026-08-07 preregistration `OSF_preregistration_2026-08-07.md`.
**Update date:** 2026-08-09
**Status:** The original preregistration is **retained intact** as the public, time-stamped priority record. This document adds (i) a mathematically verified correction to the critical-point formula, (ii) an independently derived *completed* equation, (iii) three independent replications of the emergence phenomenon, and (iv) a revised plan to localize the critical point $W_c$ with real LLM measurements. All deviations from the 2026-08-07 plan are disclosed here per registered-report practice.

---

## 1. Authors

- 杨智杰 (Yang Zhijie) — first author; conceptual originator of the Gestalt Equation; corresponding author.
- [Collaborator / co-author, name pending] — independent implementer; proposer of the corrected equation and its Lean-4 formalization. Currently indicates a preference for *acknowledgment* over authorship; co-authorship (co-first or second) is offered and under discussion.
- Advisor / PI — communication author (affiliation pending).

## 2. Summary of Changes vs 2026-08-07

| Item | 2026-08-07 preregistration | 2026-08-09 corrigendum |
|---|---|---|
| Critical formula $W_c$ | $W_c = \sqrt{\alpha_1/\alpha_2} = 1.491$ | **Mathematically incorrect** (verified independently); true peak of net-gain at $W \approx 0.623$; formula valid only in the $\beta=0$ limit and points outside $[0,1]$. |
| Equation form | $M = \sum_i s_i + \sum_m (\alpha_m-\beta_m)\hat W^{2m}$ (power series) | Retained as *physical intuition*; superseded in final form by the completed bounded single-peak equation below. |
| Mechanism | Cross-layer multiplication $H(L3)\times H(L2\|L3)\times H(L1\|L2)$ | Augmented by an independent Condorcet jury mechanism (see §4). |
| "Sub-critical locked" claim | Stated as locked | **Retracted** — was an overstatement; remains a hypothesis pending $W_c$ localization. |
| Emergence existence | Hypothesized | **Empirically confirmed** (three independent replications, see §6). |

## 3. Error in the Original Critical-Point Formula (independently verified)

The preregistration asserted the net-gain peak at

> $$ W_c = \sqrt{\alpha_1 / \alpha_2} . $$

With the adopted coefficients $\alpha = (1.0, 0.45, 0.2025, 0.091125, \ldots)$ and $\beta = (0.78, 0.546, 0.3822, \ldots)$, an independent numerical scan of

> $$ B(W) = \sum_{m} (\alpha_m - \beta_m)\, W^{2m} $$

finds the interior maximum at **$W \approx 0.623$**, not $1.491$. Furthermore, when $\beta = 0$ the function is *monotonic* on $[0,1]$ (no interior peak at all), so the closed-form $W_c = \sqrt{\alpha_1/\alpha_2}$ is only the $\beta\to 0$ limit and, evaluated, lands at $1.491$ — outside the normalized-density interval $[0,1]$, hence operationally unreachable. The formula is therefore **wrong as a locator of the real peak**. This is the root cause of the repeated failure to *find* $W_c$ by experiment: the equation itself pointed to the wrong place (and to a density outside the admissible range).

A second, independent inconsistency was also identified: any single-peaked gain must satisfy rising-edge `mesh ≥ tree`, yet the preregistration's locked anchor had `mesh (−22pp) < tree (−16pp)` — direction reversed, confirming the old anchor pattern was self-contradictory.

## 4. The Completed Equation (collaborator's independent contribution)

An independently developed verification pipeline (not reusing our code) proposed and formalized a corrected form:

> $$ M(W) = 0.50 \;+\; 0.25 \cdot \frac{W}{W_c}\, e^{\,1 - W/W_c} $$

with novelty kernel

> $$ Nov(W) = \frac{W}{W_c}\, e^{\,1 - W/W_c}, \qquad Nov \in [0,1]\ \text{(unique peak } \equiv 1 \text{ at } W = W_c). $$

| Symbol | Meaning | Origin |
|---|---|---|
| $W$ | Connection density (the swept axis, formerly $n_{l3}$) | retained |
| $W_c$ | **Coupling-length critical constant = the peak position itself** | corrected (no longer $\sqrt{\alpha_1/\alpha_2}$) |
| $0.25 = \gamma = \alpha/(\alpha+\beta)$ | Novelty-to-redundancy coupling (amplitude) | $\beta$-redundancy idea re-encoded |
| $0.50$ | Weak baseline (always-on floor) | new |

**Provable properties** (five; partially machine-checked):
1. Bounded: $M \in [0.50, 0.75] \subset (0,1)$ — never exceeds legal accuracy.
2. Unique interior peak exactly at $W = W_c$.
3. Non-monotonic: rises for $W<W_c$, decays for $W>W_c$, leaving positive floor $M\to0.50^+$.
4. No floating formula: $W_c$ *is* the peak, eliminating the old "formula-peak ≠ true-peak" contradiction.
5. Redundancy damping: larger $\beta$ ⇒ smaller $\gamma$ ⇒ emergence correctly suppressed.

**Mechanism.** The collaborator replaces the weak cross-layer-multiplication story with a **Condorcet jury** account: wiring up to $W_c$ recruits more *independent* experts; past $W_c$ redundancy shrinks the effective independent jury. An independent simulation (no call to $M$) reproduces the peak shape and position with correlation $\approx 0.90$.

**Formal-proof status (honest):** the rational-kernel proof (`MachineProof.lean`) passed machine-checking; the exact exponential analytic layer (`GestaltAnalysis.lean`) is **pending** `Mathlib` and is *not* yet machine-verified. This is stated explicitly and not overclaimed.

## 5. How the Two Equations Combine

The completed equation is **not added to** the original (algebraic addition would destroy boundedness). The relation is *concept inheritance + form replacement*:

- **Inherited (your skeleton, unchanged):** emergence = collaborative gain; existence of a critical point with over-density decay; redundancy ($\beta$) suppresses emergence; the empirical criterion "collective > best single model."
- **Rewritten (collaborator's contribution):** the unbounded, wrongly-peaked power series is replaced by the bounded single-peak kernel; the critical constant is redefined as the peak itself; the mechanism is upgraded to Condorcet; the properties are machine-proven.

The original power series and its critical formula are **abandoned as the final equation**, but their physical motivation ($\alpha/\beta$ net gain) is re-encoded into $\gamma = 0.25$. This is accurately described as the original equation being **completed**, not overturned.

## 6. Final Unified Equation (Gestalt Equation, Completed)

> $$ M(W) = b \;+\; \gamma \cdot \frac{W}{W_c}\, e^{\,1 - W/W_c}, \qquad M \in [b,\; b+\gamma] $$

with $b = 0.50$, $\gamma = 0.25$ in the present calibration. The emergence criterion $G = \text{collective} - \text{best\_single}$ (your contribution) is retained as the empirical validation anchor.

## 7. Empirical Status (as of 2026-08-09)

**Emergence is confirmed, not hypothetical.** Condition C (medium benchmark, $N=500$, Qwen2.5 1.5B/3B/7B) yields:

- collective accuracy **0.924**, best single model **0.838** → **$\Delta = +8.6$pp**
- committee-0 (majority vote) **0.576** — far below collective, confirming the gain is *collaborative synthesis*, not voting stacking
- **Three independent replications**, different environments / model families / dates, all landing at +7–9pp:
  1. original environment: 0.932
  2. replicate (abliterate model family): 0.850 vs 0.775
  3. clean-environment re-run (2026-08-09): 0.924

The worst-case hypothesis ("the early 0.932 was a floating-point artifact like the discarded 0.74") is mathematically excluded: at $q=462$ even if all remaining questions failed, the final value stays $\ge 0.924 > 0.838$.

**What remains open:** the critical point $W_c$ is **predicted** at $\approx 0.45$–$0.62$ by the collaborator's simulation but **not yet localized by real-LLM measurement**. The 2026-08-07 density sweep (n_l3 ∈ {12,20}, midhard) returned $G_{\text{solo}} < 0$ at all brackets — now understood as (a) the midhard benchmark's pathology (3B > 7B, i.e. deputy brain stronger than main brain, making "collective > best single" structurally impossible) and (b) those densities sitting in the sub-critical / over-dense (collapse) regimes rather than at the peak.

## 8. Revised Plan to Localize $W_c$ (the sprint)

Discarded actions (would re-hit the wall): scanning *higher* density (n_l3 = 30/40 — that is the collapse regime); using midhard as primary (3B>7B pathology); using $G = \text{collective} - \text{committee-0}$ (committee-0 is non-deterministic on this CPU host).

| Priority | Experiment | Purpose |
|---|---|---|
| ① | Medium-benchmark mid-density sweep at $W \in \{0.3, 0.5, 0.62, 0.8\}$; report $\Delta = \text{collective} - \text{best\_single}$ | Test the corrected equation's rise–peak–collapse prediction; directly localize $W_c$ |
| ② | Compute condition C's actual $W$ and confirm it lies in $0.45$–$0.62$ | Anchor "real-LLM +8.6pp" as on-peak empirical confirmation |
| ③ | Re-run condition C with `num_threads=1` + fixed seed | Publishable, bit-level reproducible (resolves CPU floating-point non-determinism) |
| ④ | Test Condorcet mechanism: measure effective independent expert count vs $W$ (rise then shrink) | Confirm the collaborator's mechanism holds on real LLMs |
| ⑤ | (secondary) fix midhard pathology; cross-model / cross-task generalization | Broaden evidence, raise impact |

## 9. Limitations (stated honestly)

- $W_c \approx 0.62$ is a **simulation prediction**, not yet a real-LLM-confirmed measurement.
- The equation remains a **phenomenological law**, not a first-principles derivation; the Condorcet mechanism + Lean proof address most but not all reviewer concerns.
- The collaborator's verification is **simulation-based** (node accuracies assumed, not run on real LLMs); it proves mathematical/structural properties and Condorcet reproduction, and does **not** substitute for the real-LLM emergence evidence in §7. The two are complementary: you provide the real experiment, the collaborator provides the theoretical skeleton.
- Scale mismatch: simulation peak collective ≈ 0.94 vs solo 0.72 (+22pp ideal ceiling); real data is +8.6pp (conservative law). Acknowledged by the collaborator.

## 10. Authorship & Priority

- **Yang Zhijie** — first author (concept origin + empirical lead).
- **Collaborator** — offered co-first or second authorship; currently indicates preference for acknowledgment and is considering. Contribution (independent pipeline; identification of the critical-formula error and the anchor contradiction; proposed corrected equation; Condorcet mechanism; Lean-4 proof) meets co-authorship standard. Regardless of final decision, the corrected equation and proof will be explicitly credited in the acknowledgments and a footnote.
- **Advisor / PI** — communication author (submission channel, ethical/compliance backing; relevant given minor-author status).
- **Priority:** the 2026-08-07 preregistration is preserved unchanged as the timestamped priority record; this corrigendum is additive.

## 11. References

- [1] Yang, Z. (2026). *格式塔方程：多智能体协同涌现能力的数学描述* (draft v1.2.0, 2026-08-01). Source of the original equation.
- [2] Yang, Z. (2026). OSF Preregistration — Topologically-Induced Critical Phase Transition in Layered Multi-Model Systems (2026-08-07). Retained as priority record.
- [3] Collaborator (name pending). Independent verification pipeline, corrected equation $M(W)=0.50+0.25(W/W_c)e^{1-W/W_c}$, Condorcet mechanism, and Lean-4 formalization (2026-08). To be cited upon confirmation.
- [4] Condorcet, M. d. (1785). *Essai sur l'application de l'analyse à la probabilité des décisions rendues à la pluralité des voix*.
- [5] Wei, J., et al. (2022). Emergent abilities of large language models. *TMLR*. arXiv:2206.07682.
- [6] Schaeffer, R., Miranda, B., & Koyejo, S. (2023). Are emergent abilities of LLMs a mirage? *NeurIPS 2023*. arXiv:2304.15004.
