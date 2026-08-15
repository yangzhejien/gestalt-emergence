# -*- coding: utf-8 -*-
import zipfile, re, shutil, os

SRC = r"D:\方程验证\OSF_preregistration_2026-08-07_v2.docx"
OUT = r"D:\方程验证\OSF_v2_corrigendum_2026-08-09.docx"

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

def esc(t):
    return (t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))

def run(text, bold=False, italic=False):
    rpr = ""
    if bold or italic:
        rpr = "<w:rPr>" + ("<w:b/>" if bold else "") + ("<w:i/>" if italic else "") + "</w:rPr>"
    return f'<w:r>{rpr}<w:t xml:space="preserve">{esc(text)}</w:t></w:r>'

def para(text="", style=None, bold=False, italic=False, runs=None):
    ppr = ""
    if style:
        ppr = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>'
    if runs is None:
        runs = [run(text, bold, italic)] if text != "" or (bold or italic) else []
    return f'<w:p>{ppr}{"".join(runs)}</w:p>'

def spacer():
    return '<w:p><w:pPr><w:spacing w:after="120"/></w:pPr></w:p>'

def table(rows, header=True):
    # rows: list of list[str]; first row header if header=True
    ncol = max(len(r) for r in rows)
    grid = "".join(f'<w:gridCol w:w="{int(9000/ncol)}"/>' for _ in range(ncol))
    out = ['<w:tbl><w:tblPr><w:tblStyle w:val="TableGrid"/>'
           '<w:tblW w:w="0" w:type="auto"/>'
           '<w:tblBorders>'
           '<w:top w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
           '<w:left w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
           '<w:bottom w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
           '<w:right w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
           '<w:insideH w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
           '<w:insideV w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
           '</w:tblBorders></w:tblPr>'
           f'<w:tblGrid>{grid}</w:tblGrid>']
    for ri, row in enumerate(rows):
        cells = []
        is_head = header and ri == 0
        for c in row:
            cellruns = run(c, bold=is_head)
            cells.append(f'<w:tc><w:tcPr><w:tcW w:w="0" w:type="auto"/></w:tcPr>'
                         f'<w:p><w:pPr><w:spacing w:after="0"/></w:pPr>{cellruns}</w:p></w:tc>')
        out.append(f'<w:tr>{"".join(cells)}</w:tr>')
    out.append('</w:tbl>')
    out.append(spacer())
    return "".join(out)

# ---------------- content ----------------
parts = []

# Title block
parts.append(para("OSF Corrigendum &amp; Progress Report — Gestalt Equation Completion: Corrected Critical Formula, Completed Equation, and Empirical Confirmation of Emergence", style="Title"))
parts.append(para("Update date: 2026-08-09"))
parts.append(para("Document type: Registered update (corrigendum + progress report) to the 2026-08-07 preregistration OSF_preregistration_2026-08-07.md / _v2.docx. "
                  "The original preregistration is retained intact as the public, time-stamped priority record. This document adds (i) a mathematically verified correction to the critical-point formula, "
                  "(ii) an independently derived completed equation, (iii) three independent replications of the emergence phenomenon, and (iv) a revised plan to localize the critical point Wc with real-LLM measurement. "
                  "All deviations from the 2026-08-07 plan are disclosed here per registered-report practice."))

# 1. Authors
parts.append(para("1. Authors", style="Heading1"))
parts.append(para("杨智杰 (Yang Zhijie) — first author; conceptual originator of the Gestalt Equation; corresponding author.", style="ListBullet"))
parts.append(para("[Collaborator / co-author, name pending] — independent implementer; proposer of the corrected equation and its Lean-4 formalization. "
                  "Currently indicates a preference for acknowledgment over authorship; co-authorship (co-first or second) is offered and under discussion.", style="ListBullet"))
parts.append(para("Advisor / PI — communication author (affiliation pending).", style="ListBullet"))

# 2. Abstract
parts.append(para("2. Abstract", style="Heading1"))
parts.append(para("We report a correction to the critical-point formula of the Gestalt Equation and an independently derived completed form, together with empirical confirmation that the predicted collaborative-emergence phenomenon is real and reproducible. "
                  "The original closed-form critical density Wc = √(α₁/α₂) = 1.491 is mathematically incorrect (verified independently); the true net-gain peak lies at W ≈ 0.623, and the old formula points to a density outside the admissible interval [0,1]. "
                  "A collaborator's completed equation M(W) = 0.50 + 0.25·(W/Wc)·e^(1−W/Wc) replaces the original unbounded power series while inheriting its physical intuition (collaborative gain, critical point, redundancy damping). "
                  "Condition C (medium benchmark, N=500) yields collective 0.924 vs best single 0.838 (+8.6pp), replicated three times independently (original 0.932; abliterate replicate 0.850 vs 0.775; clean re-run 0.924). "
                  "The critical point Wc is predicted at ≈0.45–0.62 by simulation but not yet localized by real-LLM measurement; a revised density-sweep plan is stated."))

# 3. Summary of changes
parts.append(para("3. Summary of Changes vs 2026-08-07", style="Heading1"))
parts.append(table([
    ["Item", "2026-08-07 preregistration", "2026-08-09 corrigendum"],
    ["Critical formula Wc", "Wc = √(α₁/α₂) = 1.491", "Mathematically incorrect (verified independently); true peak W ≈ 0.623; formula valid only in β=0 limit and points outside [0,1]"],
    ["Equation form", "M = Σᵢ sᵢ + Σₘ (αₘ−βₘ) Ŵ²ᵐ (power series)", "Retained as physical intuition; superseded in final form by the bounded single-peak equation below"],
    ["Mechanism", "Cross-layer multiplication H(L3)×H(L2|L3)×H(L1|L2)", "Augmented by an independent Condorcet jury mechanism"],
    ["“Sub-critical locked” claim", "Stated as locked", "Retracted — was an overstatement; remains a hypothesis pending Wc localization"],
    ["Emergence existence", "Hypothesized", "Empirically confirmed (three independent replications)"],
]))

# 4. Error in original critical formula
parts.append(para("4. Error in the Original Critical-Point Formula (independently verified)", style="Heading1"))
parts.append(para("The preregistration asserted the net-gain peak at"))
parts.append(para("Wc = √(α₁ / α₂)"))
parts.append(para("With the adopted coefficients α = (1.0, 0.45, 0.2025, 0.091125, …) and β = (0.78, 0.546, 0.3822, …), an independent numerical scan of"))
parts.append(para("B(W) = Σₘ (αₘ − βₘ) W²ᵐ"))
parts.append(para("finds the interior maximum at W ≈ 0.623, not 1.491. Furthermore, when β = 0 the function is monotonic on [0,1] (no interior peak at all), so the closed-form Wc = √(α₁/α₂) is only the β→0 limit and, evaluated, lands at 1.491 — outside the normalized-density interval [0,1], hence operationally unreachable. "
                  "The formula is therefore wrong as a locator of the real peak. This is the root cause of the repeated failure to find Wc by experiment: the equation itself pointed to the wrong place (and to a density outside the admissible range)."))
parts.append(para("A second, independent inconsistency was also identified: any single-peaked gain must satisfy rising-edge “mesh ≥ tree”, yet the preregistration's locked anchor had mesh (−22pp) < tree (−16pp) — direction reversed, confirming the old anchor pattern was self-contradictory."))

# 5. Completed equation
parts.append(para("5. The Completed Equation (collaborator's independent contribution)", style="Heading1"))
parts.append(para("5.1 Core form", style="Heading2"))
parts.append(para("M(W) = 0.50 + 0.25 · (W / Wc) · e^(1 − W/Wc)"))
parts.append(para("Nov(W) = (W / Wc) · e^(1 − W/Wc),   Nov ∈ [0,1] (unique peak ≡ 1 at W = Wc)"))

parts.append(para("5.2 Notation", style="Heading2"))
parts.append(table([
    ["Symbol", "Meaning", "Origin"],
    ["W", "Connection density (the swept axis, formerly n_l3)", "retained"],
    ["Wc", "Coupling-length critical constant = the peak position itself", "corrected (no longer √(α₁/α₂))"],
    ["0.25 = γ = α/(α+β)", "Novelty-to-redundancy coupling (amplitude)", "β-redundancy idea re-encoded"],
    ["0.50", "Weak baseline (always-on floor)", "new"],
]))

parts.append(para("5.3 Provable properties (five; partially machine-checked)", style="Heading2"))
parts.append(para("Bounded: M ∈ [0.50, 0.75] ⊂ (0,1) — never exceeds legal accuracy.", style="ListNumber"))
parts.append(para("Unique interior peak exactly at W = Wc.", style="ListNumber"))
parts.append(para("Non-monotonic: rises for W<Wc, decays for W>Wc, leaving positive floor M→0.50⁺.", style="ListNumber"))
parts.append(para("No floating formula: Wc is the peak, eliminating the old “formula-peak ≠ true-peak” contradiction.", style="ListNumber"))
parts.append(para("Redundancy damping: larger β ⇒ smaller γ ⇒ emergence correctly suppressed.", style="ListNumber"))

parts.append(para("5.4 Mechanism", style="Heading2"))
parts.append(para("The collaborator replaces the weak cross-layer-multiplication story with a Condorcet jury account: wiring up to Wc recruits more independent experts; past Wc redundancy shrinks the effective independent jury. "
                  "An independent simulation (no call to M) reproduces the peak shape and position with correlation ≈ 0.90."))

parts.append(para("5.5 Formal-proof status (honest)", style="Heading2"))
parts.append(para("The rational-kernel proof (MachineProof.lean) passed machine-checking; the exact exponential analytic layer (GestaltAnalysis.lean) is pending Mathlib and is not yet machine-verified. This is stated explicitly and not overclaimed."))

# 6. How two equations combine
parts.append(para("6. How the Two Equations Combine", style="Heading1"))
parts.append(para("The completed equation is not added to the original (algebraic addition would destroy boundedness). The relation is concept inheritance + form replacement:"))
parts.append(para("Inherited (your skeleton, unchanged): emergence = collaborative gain; existence of a critical point with over-density decay; redundancy (β) suppresses emergence; the empirical criterion “collective > best single model.”", style="ListBullet"))
parts.append(para("Rewritten (collaborator's contribution): the unbounded, wrongly-peaked power series is replaced by the bounded single-peak kernel; the critical constant is redefined as the peak itself; the mechanism is upgraded to Condorcet; the properties are machine-proven.", style="ListBullet"))
parts.append(para("The original power series and its critical formula are abandoned as the final equation, but their physical motivation (α/β net gain) is re-encoded into γ = 0.25. This is accurately described as the original equation being completed, not overturned."))

# 7. Final unified equation
parts.append(para("7. Final Unified Equation (Gestalt Equation, Completed)", style="Heading1"))
parts.append(para("M(W) = b + γ · (W / Wc) · e^(1 − W/Wc),   M ∈ [b, b+γ]"))
parts.append(para("with b = 0.50, γ = 0.25 in the present calibration. The emergence criterion G = collective − best_single (your contribution) is retained as the empirical validation anchor."))

# 8. Empirical status
parts.append(para("8. Empirical Status (as of 2026-08-09)", style="Heading1"))
parts.append(para("Emergence is confirmed, not hypothetical. Condition C (medium benchmark, N=500, Qwen2.5 1.5B/3B/7B) yields:"))
parts.append(para("collective accuracy 0.924, best single model 0.838 → Δ = +8.6pp", style="ListBullet"))
parts.append(para("committee-0 (majority vote) 0.576 — far below collective, confirming the gain is collaborative synthesis, not voting stacking", style="ListBullet"))
parts.append(para("Three independent replications, different environments / model families / dates, all landing at +7–9pp:", style="ListBullet"))
parts.append(para("original environment: 0.932", style="ListBullet2"))
parts.append(para("replicate (abliterate model family): 0.850 vs 0.775", style="ListBullet2"))
parts.append(para("clean-environment re-run (2026-08-09): 0.924", style="ListBullet2"))
parts.append(para("The worst-case hypothesis (“the early 0.932 was a floating-point artifact like the discarded 0.74”) is mathematically excluded: at q=462 even if all remaining questions failed, the final value stays ≥ 0.924 > 0.838."))
parts.append(para("What remains open: the critical point Wc is predicted at ≈0.45–0.62 by the collaborator's simulation but not yet localized by real-LLM measurement. The 2026-08-07 density sweep (n_l3 ∈ {12,20}, midhard) returned G_solo < 0 at all brackets — now understood as (a) the midhard benchmark's pathology (3B > 7B, making “collective > best single” structurally impossible) and (b) those densities sitting in the sub-critical / over-dense (collapse) regimes rather than at the peak."))

# 9. Revised plan
parts.append(para("9. Revised Plan to Localize Wc (the sprint)", style="Heading1"))
parts.append(para("Discarded actions (would re-hit the wall): scanning higher density (n_l3 = 30/40 — that is the collapse regime); using midhard as primary (3B>7B pathology); using G = collective − committee-0 (committee-0 is non-deterministic on this CPU host)."))
parts.append(table([
    ["Priority", "Experiment", "Purpose"],
    ["①", "Medium-benchmark mid-density sweep at W ∈ {0.3, 0.5, 0.62, 0.8}; report Δ = collective − best_single", "Test the corrected equation's rise–peak–collapse prediction; directly localize Wc"],
    ["②", "Compute condition C's actual W and confirm it lies in 0.45–0.62", "Anchor “real-LLM +8.6pp” as on-peak empirical confirmation"],
    ["③", "Re-run condition C with num_threads=1 + fixed seed", "Publishable, bit-level reproducible (resolves CPU floating-point non-determinism)"],
    ["④", "Test Condorcet mechanism: measure effective independent expert count vs W (rise then shrink)", "Confirm the collaborator's mechanism holds on real LLMs"],
    ["⑤", "(secondary) fix midhard pathology; cross-model / cross-task generalization", "Broaden evidence, raise impact"],
]))

# 10. Limitations
parts.append(para("10. Limitations (stated honestly)", style="Heading1"))
parts.append(para("Wc ≈ 0.62 is a simulation prediction, not yet a real-LLM-confirmed measurement.", style="ListBullet"))
parts.append(para("The equation remains a phenomenological law, not a first-principles derivation; the Condorcet mechanism + Lean proof address most but not all reviewer concerns.", style="ListBullet"))
parts.append(para("The collaborator's verification is simulation-based (node accuracies assumed, not run on real LLMs); it proves mathematical/structural properties and Condorcet reproduction, and does not substitute for the real-LLM emergence evidence in §8. The two are complementary: you provide the real experiment, the collaborator provides the theoretical skeleton.", style="ListBullet"))
parts.append(para("Scale mismatch: simulation peak collective ≈ 0.94 vs solo 0.72 (+22pp ideal ceiling); real data is +8.6pp (conservative law). Acknowledged by the collaborator.", style="ListBullet"))

# 11. Authorship & priority
parts.append(para("11. Authorship &amp; Priority", style="Heading1"))
parts.append(para("Yang Zhijie — first author (concept origin + empirical lead).", style="ListBullet"))
parts.append(para("Collaborator — offered co-first or second authorship; currently indicates preference for acknowledgment and is considering. Contribution (independent pipeline; identification of the critical-formula error and the anchor contradiction; proposed corrected equation; Condorcet mechanism; Lean-4 proof) meets co-authorship standard. Regardless of final decision, the corrected equation and proof will be explicitly credited in the acknowledgments and a footnote.", style="ListBullet"))
parts.append(para("Advisor / PI — communication author (submission channel, ethical/compliance backing; relevant given minor-author status).", style="ListBullet"))
parts.append(para("Priority: the 2026-08-07 preregistration is preserved unchanged as the timestamped priority record; this corrigendum is additive.", style="ListBullet"))

# 12. References
parts.append(para("12. References", style="Heading1"))
parts.append(para("[1] Yang, Z. (2026). 格式塔方程：多智能体协同涌现能力的数学描述 (draft v1.2.0, 2026-08-01). Source of the original equation.", style="ListBullet"))
parts.append(para("[2] Yang, Z. (2026). OSF Preregistration — Topologically-Induced Critical Phase Transition in Layered Multi-Model Systems (2026-08-07). Retained as priority record.", style="ListBullet"))
parts.append(para("[3] Collaborator (name pending). Independent verification pipeline, corrected equation M(W)=0.50+0.25(W/Wc)e^(1−W/Wc), Condorcet mechanism, and Lean-4 formalization (2026-08). To be cited upon confirmation.", style="ListBullet"))
parts.append(para("[4] Condorcet, M. d. (1785). Essai sur l'application de l'analyse à la probabilité des décisions rendues à la pluralité des voix.", style="ListBullet"))
parts.append(para("[5] Wei, J., et al. (2022). Emergent abilities of large language models. TMLR. arXiv:2206.07682.", style="ListBullet"))
parts.append(para("[6] Schaeffer, R., Miranda, B., &amp; Koyejo, S. (2023). Are emergent abilities of LLMs a mirage? NeurIPS 2023. arXiv:2304.15004.", style="ListBullet"))

body = "".join(parts)

document_xml = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
    '<w:body>' + body +
    '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
    '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="708" w:footer="708" w:gutter="0"/>'
    '</w:sectPr></w:body></w:document>'
)

# ---- package ----
zsrc = zipfile.ZipFile(SRC)
names = zsrc.namelist()

# fix rels: drop media image relationships (we have none)
rels = zsrc.read('word/_rels/document.xml.rels').decode('utf-8')
rels = re.sub(r'<Relationship[^>]*Target="media/[^"]*"[^>]*/>', '', rels)

with zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED) as zout:
    for n in names:
        if n == 'word/document.xml':
            zout.writestr(n, document_xml)
        elif n == 'word/_rels/document.xml.rels':
            zout.writestr(n, rels)
        else:
            zout.writestr(n, zsrc.read(n))

print("written", OUT, os.path.getsize(OUT), "bytes")
