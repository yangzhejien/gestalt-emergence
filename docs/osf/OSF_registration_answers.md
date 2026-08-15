# OSF 登记册「Theory-based Predictions」字段填写草稿
> 用于：格式塔方程的拓扑诱导临界相变预注册
> 填写说明：以下每段即对应 OSF 模板的一个字段，直接复制粘贴。
> ⚠️ 诚实披露红线：亚临界三档（tree@12 / mesh@12 / full@12）**数据已收完并锁定**，必须在「背景」与「范围条件案件」中如实写明；full@20 为**前瞻性（尚未收集）**测试，注册后不得改动预测。

---

## 一、理论与测量

### 1. 背景（Background）
本预注册检验「格式塔方程」（Gestalt Equation）的一项核心预测：分层多模型系统（layered multi-model system）在集体准确率上是否表现出**拓扑诱导的临界相变**——即系统的净涌现增益随节点间连接密度 \(\hat W\) 非单调变化，并在临界密度 \(W_c=\sqrt{\alpha_1/\alpha_2}\) 处出现峰值。

理论包含两个涌现路径：(A) **结构性跨层涌现**——各层对上一层输出做加工而非简单投票，整体能力 \(H_{\text{total}}=H(L3)\times H(L2\mid L3)\times H(L1\mid L2)\)，表现为集体准确率高于纯投票（committee-0）与最强单体（solo-7B）；(B) **密度超线性涌现**——当跨层连接密度超过阈值 \(W_c\) 时，净涌现由负转正，形成临界相变。方程采用带符号修正 \(M=\sum_i s_i+\sum_m(\alpha_m-\beta_m)\hat W^{2m}\)，其中 \(\beta_m\) 项表示过密时的负干涉，使净涌现呈非单调（存在最优密度）。

**理论渊源**：本理论为研究者**原创**，除本预注册及随附草稿（Yang, 2026, v1.2.0）外，**未在其他地方发表**。其学术背景置于以下文献脉络中：涌现的层级性（Anderson, 1972, *Science*, "More is Different"）、协同学（Haken）与弱涌现（Bedau, 1997）；临界现象与相变（Stauffer & Aharony 渗流理论；Buldyrev et al., 2010, *Nature* 464:1025，跨层耦合网络的相变类比；Beggs & Plenz, 2003, *J. Neurosci.* 23:11167，神经元雪崩临界态）；混合专家与分层模型（Jacobs et al., 1991, *Neural Computation* 3:79；Fedus et al., 2022, *JMLR* 23:120，Switch Transformers；Jiang et al., 2024, arXiv:2401.04088，Mixtral）；以及大模型规模/涌现（Kaplan et al., 2020；Wei et al., 2022, arXiv:2206.07682，LLM 涌现能力；Schaeffer et al., 2023，对"涌现是度量假象"的警示，构成本研究的方法学护栏）。

**数据状态披露**：截至本注册日（2026-08-07），亚临界三档（tree@12、mesh@12、full@12，各 n=50）实验**已完成并锁定**（实测：tree 集体 58.0%、mesh 52.0%、full@12 64.0%；相对 solo-7B 的净涌现分别为 −16pp / −22pp / −10pp；相对 committee-0 均为 +14pp 左右）。后临界档 full@20（n=50）**尚未收集**，构成本预注册的前瞻性检验；此前仅有一个 n=6 的探索性锚点（集体 > solo 约 +17pp，95% CI ≈ ±30pp，极宽，不具统计结论力）。

### 2. 范围条件案件（Scope / Conditions / Cases）
理论适用的情形：**使用分层拓扑（顶层编排 L1 / 中层副导 L2 / 底层专家集群 L3）连接、节点为具备实值单模型能力（\(s_i>\) 随机）的语言模型、且节点间存在跨层连接的系统**。预测在该范围内、于以下尽可能多的"案例"（密度扫描档位）上统一注册，避免挑选有利案例：

- tree@12（低密度，\(\hat W\) 最小）
- mesh@12（中低密度）
- full@12（中高密度；G_solo<0，与亚临界假设一致，Wc 尚未定位）
- full@20（高密度，预期后临界右翼）
- （可选）更高密度过连接点（如 full@20+额外 L3 内连，或更大 n_l3），用于检验 \(\beta\) 项导致的峰值后回落

**时间范围**：注册日 2026-08-07 至实验完成日（目标 2026-12-31；若届时未完，以实际完成日为准，注册后不追溯修改预测）。
**地理范围**：N/A（纯计算实验，无地理适用边界）。

---

## 二、研究变量

### 3. 可变规格（Variable Specification）
- **自变量**：拓扑连接密度 \(\hat W\)（操作化为 tree → mesh → full 三级拓扑，及节点规模 \(n_{l3}\in\{12,20\}\)）。
- **主要结局变量**：净涌现 \(\Delta = A_{\text{coll}} - A_{\text{baseline}}\)，其中 \(A_{\text{coll}}\) 为分层系统集体准确率，\(A_{\text{baseline}}\) 取 solo-7B 或 committee-0（分别报告）。
- **辅助结局变量**：committee-0 准确率 \(A_{\text{comm0}}\)（L3 多数投票，纯加性池化）、solo-7B 准确率 \(A_{\text{solo7B}}\)、各层单模型准确率 \(s_i\)（1.5B / 3B / 7B）。
- **中介变量**：各层加工熵 \(H(L3)\)、\(H(L2\mid L3)\)、\(H(L1\mid L2)\)——跨层乘法链，解释结构性涌现如何产生。
- **调节变量**：密度区制（亚临界：Ŵ 低于 Wc；后临界：Ŵ 高于 Wc）；模型族（Qwen2.5）。

### 4. 变量关系（Variable Relationships）
理论预测的方向性：
- **H1（结构性，任何拓扑内）**：\(A_{\text{coll}} > A_{\text{comm0}}\) 且 \(A_{\text{coll}} > A_{\text{solo7B}}\)（跨层乘法使集体超过纯投票与最强单体）。
- **H2（临界相变，密度扫描）**：净涌现 \(\Delta\) 随 \(\hat W\) 呈**非单调**变化——在 \(W_c\) 左侧（亚临界）\(\Delta \le 0\)（无超线性增益，集体不超过最强单体）；在右侧（后临界）\(\Delta > 0\)；峰值位于 \(W_c=\sqrt{\alpha_1/\alpha_2}\)，过密后由 \(\beta\) 项回落。注册的排序预测：\(\Delta(\text{tree}) \le \Delta(\text{mesh}) \le \Delta(\text{full@12}) < 0 < \Delta(\text{full@20})\)，且在某更高密度点出现峰值后下降。

### 5. 可变测量（Variable Measurement）——见下「测量与数据」
### 6. 测量与数据（Measurement & Data）
- **基准**：密度扫描所用为 mcq_midhard_clean.jsonl（250 题，band_ok=True）；另有 mcq_medium_clean.jsonl（500 题）作难度带校准对照。每档抽 n=50。
- **模型**：Qwen2.5 1.5B / 3B / 7B，本地 Ollama 服务（127.0.0.1:11434）。
- **采集**：每题独立生成、逐题检查点续跑；单实例锁防并发踩踏；full@12 收尾后 CPU 释放可做探针。
- **处理**：每档计算 \(A_{\text{coll}}\)、\(A_{\text{comm0}}\)、\(A_{\text{solo7B}}\)；\(\Delta = A_{\text{coll}} - A_{\text{baseline}}\)；报告 95% 置信区间（wald 比例 CI）。
- **来源**：原始数据为本研究自行生成，非公开数据集。

### 7. 缺失数据（Missing Data）
设计上每档 n=50 完整。生成失败的题目在检查点续跑中重试；若最终剔除，报告有效 n 并说明原因；**不插补**（imputation N/A），以保证 \(\Delta\) 与 CI 的可解释性。

---

## 三、评估指标

### 8. 预测准确性（Prediction Accuracy）
- **主要指标**：密度扫描中**各档净涌现符号（\(\Delta\) 正负）与理论预测模式的一致比例**。注册模式为 4 档：tree / mesh / full@12 预测 \(\Delta<0\)，full@20 预测 \(\Delta>0\)。一致比例 = 符号正确的档数 / 总档数。
- **连续检验（鲁棒性）**：(a) \(\Delta\) 从 tree→mesh→full@12 是否单调趋近 0（亚临界左翼成立）；(b) full@20 是否 \(\Delta>0\)（后临界右翼成立）；(c) 更高密度点是否出现峰值后回落（\(\beta\) 项）。每档附 95% CI，检验预测排序在 CI 内是否保持。
- **H1 检验（鲁棒性）**：每档内 \(A_{\text{coll}} > A_{\text{comm0}}\) 与 \(> A_{\text{solo7B}}\) 的配对比较（二项 / 符号检验）。
- 选择"符号一致比例"为主要指标，因其直接检验理论的预测力；CI 排序与 H1 比较作为鲁棒性检查。

### 9. 置信水平（Confidence Levels）
序数置信度：
- n_l3=12 三档（G_solo<0，与亚临界假设一致；Wc 未定位，数值待确定性重跑确认）：**中**
- 后临界 full@20（仅 n=6 探索锚点，CI±30pp）：**低**
- \(W_c\) 峰值定位（尚未局部化）：**中**

**不将置信水平作为准确性评估的加权**（保持检验严格，避免移动门柱）；置信度仅作阅读者参考。

### 10. 替代基线（Alternative Baseline）
提供以下替代基线，供理论预测力比较：
1. **committee-0 多数投票**（纯加性池化，无跨层乘法）——代表"无结构性涌现"零模型；
2. **solo-7B 单体**（参数量大于任一节点）——检验"是否只是更大的单体模型"；
3. **（规划）随机拓扑基线**：在 full@20 同总边数下，以随机连线替代结构化跨层连线——隔离"拓扑"与"单纯算力/连接数"。

理论预测：在**结构化跨层拓扑**下，集体系统超过上述基线（尤其超过 committee-0 与 solo-7B）；而在**随机拓扑**下净涌现增益应消失。复现所需信息：基准文件、模型名/版本、拓扑构造脚本、n 与随机种子（随附于项目仓库）。

---

## 附：用于 OSF 摘要/描述的一句话
本 OSF 登记册依据 Theory-based Predictions 模板，事前声明格式塔方程的拓扑诱导临界相变预测（净涌现随连接密度在 \(W_c\) 处非单调峰值），并给出可证伪的密度扫描检验设计；亚临界三档已锁、后临界 full@20 为前瞻性测试。

---

## 四、OSF 元数据补充（注册表单的「标签」与「参考文献」字段）

> 以下两块是你之前表单里留空、导致「标签空 / 参考文献空」两项错误的地方。补上即可。

### 标签（Tags，逐条添加，OSF 用小写英文）
```
emergence
preregistration
multi-agent-systems
phase-transition
statistical-physics
large-language-models
collective-intelligence
```

### 参考文献（References，逐条粘贴；完整 27 条见随附 v2.docx §10）
1. Anderson, P. W. (1972). More is Different. *Science*, 177(4047), 393–396.
2. Buldyrev, S. V., Parshani, R., Paul, G., Stanley, H. E., & Havlin, S. (2010). Catastrophic cascade of failures in interdependent networks. *Nature*, 464, 1025–1028.
3. Beggs, J. M., & Plenz, D. (2003). Neuronal Avalanches in Neocortical Circuits. *Journal of Neuroscience*, 23(35), 11167–11177.
4. Jacobs, R. A., Jordan, M. I., Nowlan, S. J., & Hinton, G. E. (1991). Adaptive Mixtures of Local Experts. *Neural Computation*, 3(1), 79–87.
5. Fedus, W., Zoph, B., & Shazeer, N. (2022). Switch Transformers: Scaling to Trillion Parameter Models with Simple and Efficient Sparsity. *JMLR*, 23(120), 1–39.
6. Wei, J., et al. (2022). Emergent Abilities of Large Language Models. *arXiv:2206.07682*.
7. Schaeffer, R., Miranda, B., & Koyejo, S. (2023). Are Emergent Abilities of Large Language Models a Mirage? *arXiv:2304.15004*.
8. Kaplan, J., et al. (2020). Scaling Laws for Neural Language Models. *arXiv:2001.08361*.
9. Jiang, A. Q., et al. (2024). Mixtral of Experts. *arXiv:2401.04088*.
10. Haken, H. (1977). *Synergetics: An Introduction*. Springer.
11. Bedau, M. A. (1997). Weak Emergence. *Philosophical Perspectives*, 11, 375–399.
12. Stauffer, D., & Aharony, A. (1994). *Introduction to Percolation Theory* (2nd ed.). CRC Press.
