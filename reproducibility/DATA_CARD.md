# 数据与材料可用性 / 复现清单（Data & Materials Availability）

> 配套文件：`D:\方程验证\` 项目。本文件作为论文「Methods – Data Availability」附录的草稿。
> 最后更新：2026-08-10。所有基准与脚本均位于本项目仓库，可随 OSF 注册册一并公开。

---

## 1. 基准清单（Benchmark Inventory）

| 文件 | 题数 | 生成方式 | 随机种子 | 生成模型 | LLM 污染风险 | 用于 |
|---|---|---|---|---|---|---|
| `benchmark/mcq_medium_clean.jsonl` | 500 | **确定性模板生成**（非 LLM） | 扩展 `20260805`；清洗 `20260804` | —（纯 Python 模板） | **无**（答案由代码计算） | **主基准**：E1(k=1) / 条件C(k=3) / E3(k=5,7) |
| `benchmark/mcq_midhard_clean.jsonl` | 250 | **LLM 出题** | — | `qwen2.5:7b`（本地 Ollama） | 有（须披露） | ⚠️ **已取消评测资格**：人工核验 6 题全部金标准错误（正确值不在选项内/答案错填他变量），且含重复题 → 见 §7.1 |
| `benchmark/mcq_hard_clean.jsonl` | 64 | **LLM 出题** | — | `qwen2.5:7b`（本地 Ollama） | 有（须披露） | ⚠️ **已取消评测资格**：人工核验 6 题全部金标准错误（含题设自相矛盾），见 §7.1 |
| `benchmark/mcq_hard100.jsonl` | 100 | **确定性模板生成** | `20260803` | — | 无 | 备用（未进主实验） |
| `benchmark/ceval_candidate.jsonl` | 1195 | **公开集 C-Eval**（hf-mirror 拉取） | 下载 `seed=42` | — | 无（第三方标准集） | 公开集交叉验证**候选池**（见 §4） |

**关键披露**：主基准（`mcq_medium_clean.jsonl`）为算法模板生成、答案由代码计算、种子全固定，可 100% 复现且不存在 LLM 评测污染担忧。仅 `mcq_midhard_clean` 与 `mcq_hard_clean` 为题面由 `qwen2.5:7b` 生成的 LLM 基准，已在方法部分如实说明生成模型与过滤口径。**⚠️ 重要更正（2026-08-10 人工核验）**：`mcq_midhard_clean` 与 `mcq_hard_clean` 经抽样人工独立核验（各 6 题）**发现金标准答案普遍错误**——正确值不在选项内、或答案错填为另一变量值、或题设自相矛盾，且存在重复题。band_ok 过滤仅检查模型间一致性、未校验数学正确性，故未能拦截。此二集**已从评测基准中取消资格**，不得用于任何定量结论；如需"更难自造集"，须改用确定性模板生成并代码算答案（如 `mcq_hard100` 做法），逐题核验后再用。

---

## 2. 生成流水线（Provenance by Benchmark）

### 2.1 `mcq_medium_clean.jsonl`（500，主基准）
- **前身**：`mcq_medium_orig100.jsonl`（100 题，同模板族，答案由代码计算）。
- **扩展**：`scripts/expand_to_500.py` — 在 orig100 基础上**程序化生成 400 道同分布（初等数学应用题）MCQ**，正确项由构造计算保证。`SEED = 20260805`。
- **清洗**：`scripts/clean_benchmark.py` — 修复占位符、重排选项字母、重排题目顺序。`SEED = 20260804`。
- **复现性**：纯本地确定性生成，不依赖 Ollama，无偶发挂死风险。`SEED` 全固定 → 字节级可复现。

### 2.2 `mcq_midhard_clean.jsonl`（250）
- `scripts/gen_midhard_benchmark.py`：`CREATOR = "qwen2.5:7b"`，通过 Ollama 本地生成题面（`build_prompt` → `generate`，`max_tokens=3072`）。
- 生成后经 **band_ok 过滤**（见 §3）得到最终子集。
- **披露要求**：论文须注明「该题面由 `qwen2.5:7b` 生成，并经 band_ok 过滤」。

### 2.3 `mcq_hard_clean.jsonl`（64）
- `scripts/gen_hard_benchmark.py`：`CREATOR = "qwen2.5:7b"`，流程同上。
- `scripts/build_hard_clean.py`：清洗/过滤。
- 注：该集已实测违反难度铁律②（把 L2 压穿），仅作探针用途，非主结论基准。

### 2.4 `mcq_hard100.jsonl`（100，备用）
- `scripts/gen_bench.py`：**确定性模板生成**，`random.seed(20260803)`，不依赖 Ollama。未进入主实验。

---

## 3. 难度过滤口径（band_ok）

所有自造集统一采用以下 **band_ok** 标准（确保每层节点都有实值 `sᵢ > 随机`，是方程成立的物理前提）：

```
band_ok = (acc_7B < 1.0)          # 最强单体留天花板余量，给 ΣαₘẆ²ᵐ 显示空间
          AND (acc_3B > 0.25)     # 中层（L2）有实值，非失效
          AND (acc_1.5B > 0.25)   # 底层（L3）有实值，非地板
```

过滤函数贪心移除使条件不满足的题目，直至子集满足 band_ok 或不足 50 题。

---

## 4. 公开集交叉验证（C-Eval）

- 目的：用标准公开基准替代自造题，封堵审稿人对「自造题研究者自由度过大」的质疑。
- 脚本：`scripts/prep_pubbench.py`（`--download` 拉取 / `--probe` 探针+过滤）。
- 来源：`C-Eval` val 集（52 学科 parquet），经 `hf-mirror.com` 拉取，转同 schema（`question/A/B/C/D/answer/subject`）。下载 `seed=42`。
- **当前状态（2026-08-10）**：
  - ✅ 候选池 `ceval_candidate.jsonl`（1195 题）已下载。
  - ⏳ band_ok 过滤子集 `ceval_bandok_clean.jsonl` **尚未生成** → 交叉验证尚未接进实验。
  - 计划：运行 `python prep_pubbench.py --probe --sample 200`，产出 `ceval_bandok_clean.jsonl` + `ceval_probe.json`（含三模型 acc、band_ok 标志），再以其为基准跑同口径密度扫描，作为正式公开集交叉验证。

---

## 5. 模型与环境（Models & Environment）

- **节点模型（主实验）**：`qwen2.5:1.5b` / `qwen2.5:3b` / `qwen2.5:7b`（Ollama 本地托管）。
- **出题模型（LLM 基准）**：`qwen2.5:7b`。
- **推理框架**：Ollama `0.32.6`，本地部署，`ollama_url` 硬编码 `http://127.0.0.1:11434`（规避本机 IPv6 `localhost`→`::1` 死锁）。
- **采样**：实验侧 `temperature = 0.0`（近确定性）；生成脚本按各脚本默认值。
- **Python**：3.13（托管 venv）。
- **OS**：Windows（本机）。GPU 型号未在本环境捕获（`nvidia-smi` 不可用）；Ollama 自动调用本地 GPU。
- **已知坑**：本机 `localhost` 解析为 `::1`(IPv6) 而 Ollama 仅监听 `127.0.0.1`；任何 URL **必须硬编码 IPv4**，用 `localhost` 会静默永久挂起。

---

## 6. 复现命令（Reproduction Commands）

### 6.1 生成基准
```bash
python scripts/expand_to_500.py        # 生成 medium 扩展 400（SEED=20260805）
python scripts/clean_benchmark.py      # 清洗 medium（SEED=20260804）
python scripts/gen_midhard_benchmark.py   # LLM 出题（creator=qwen2.5:7b）
python scripts/gen_hard_benchmark.py      # LLM 出题（creator=qwen2.5:7b）
python scripts/build_hard_clean.py        # 清洗 hard
python scripts/gen_bench.py               # 模板生成 hard100（SEED=20260803）
```

### 6.2 主实验（密度扫描，M(k) 曲线）

**历史运行（as-run，未带种子，仅供溯源）**
```bash
# E1（k=1，亚临界基线）
python scripts/verify_stage2.py --k 1 --benchmark benchmark/mcq_medium_clean.jsonl --n 500 --conn-w 1.0 --live stage2_E1_k1.json
# 条件C（k=3，峰）
python scripts/verify_stage2.py --k 3 --benchmark benchmark/mcq_medium_clean.jsonl --n 500 --conn-w 1.0 --live stage2_condC_k3.json
# E3（k=5, k=7，降沿）
python scripts/verify_stage2.py --k 5 --benchmark benchmark/mcq_medium_clean.jsonl --n 500 --conn-w 1.0 --live stage2_E3_k5.json
python scripts/verify_stage2.py --k 7 --benchmark benchmark/mcq_medium_clean.jsonl --n 500 --conn-w 1.0 --live stage2_E3_k7.json
```

**推荐复现命令（统一带种子，字节级可复现）**
```bash
# 同口径复现（seed 固定为 20260810，同时 seed Python random 与 Ollama options.seed）
python scripts/verify_stage2.py --k 1 --benchmark benchmark/mcq_medium_clean.jsonl --n 500 --conn-w 1.0 --seed 20260810 --live stage2_E1_k1_repro.json
python scripts/verify_stage2.py --k 3 --benchmark benchmark/mcq_medium_clean.jsonl --n 500 --conn-w 1.0 --seed 20260810 --live stage2_condC_k3_repro.json
python scripts/verify_stage2.py --k 5 --benchmark benchmark/mcq_medium_clean.jsonl --n 500 --conn-w 1.0 --seed 20260810 --live stage2_E3_k5_repro.json
python scripts/verify_stage2.py --k 7 --benchmark benchmark/mcq_medium_clean.jsonl --n 500 --conn-w 1.0 --seed 20260810 --live stage2_E3_k7_repro.json
```
> 注：`verify_stage2.py` 现已支持 `--seed <int>` 参数（同时 seed Python `random` 并透传 Ollama `options.seed`，使生成可复现）。历史 E1/条件C/E3 运行**未带 `--seed`**，其复现性依赖 `temperature=0.0` 的近确定性；后续复现统一加 `--seed 20260810` 以保证字节级一致（见上方「推荐复现命令」）。

### 6.3 公开集交叉验证（C-Eval，进行中）
```bash
python scripts/prep_pubbench.py --download            # 已执行：产出 ceval_candidate.jsonl
python scripts/prep_pubbench.py --probe --sample 200  # 进行中：产出 ceval_bandok_clean.jsonl + ceval_probe.json（与 E3 共用 Ollama，错峰采样）
```

---

## 7. 已知局限与诚信声明（Limitations & Integrity Notes）

1. **LLM 生成基准金标准错误（已实证，非推测）**：`mcq_midhard/hard` 的 `answer` 由 `qwen2.5:7b` 产出、经 band_ok（模型一致性）过滤，但**未校验数学正确性**。2026-08-10 人工独立核验各抽 6 题，**12 题全部金标准错误**：正确值不在选项内（如 `3x-5=2(x+4)` 解为 13，选项无 13；记录却标 C=7）、答案错填为另一变量（如求 x 却标 y 的值）、题设自相矛盾（如递推式与给定项不符）；且存在跨题重复（midhard 内 #82=#90、#240=#12；hard 内 #6=#38=#26）。**结论**：此二集已从评测基准取消资格，不得用于任何定量结论。主结论仅依赖 `mcq_medium_clean`（模板/算答案）+ C-Eval（人工策划公开集，扫描中）。如需更难的"自造集"，须改用确定性模板生成（如 `mcq_hard100`）+ 代码算答案 + 逐题核验。
2. **实验侧随机种子（已修复）**：`verify_stage2.py` 现已支持 `--seed <int>`（透传 Ollama `options.seed` + Python `random`）。历史 E1/条件C/E3 运行**未带 `--seed`**，其复现性依赖 `temperature=0.0` 的近确定性；跨硬件/版本可能存在微小浮动。后续所有复现运行应统一加 `--seed` 并在报告中标注种子值。
3. **单基准风险**：主结论目前基于单一自造基准 `mcq_medium_clean`；C-Eval 公开集交叉验证为缓解此风险的关键补充（§4 进行中）。
4. **预注册**：本研究预测已通过 OSF 登记册预注册（Theory-based Predictions 模板），数据卡与代码随注册册公开，接受前瞻性预测核查。

---

## 8. 数据与代码可用性（Availability）

- **基准数据**：`D:\方程验证\benchmark\*.jsonl`（随论文/注册册公开）。
- **生成与实验代码**：`D:\方程验证\scripts\*.py`。
- **预注册与 corrigendum**：OSF Project（含 v2.docx + 4 图）；正式预注册 = OSF 登记册冻结快照 + 自动 DOI。
- **许可**：代码采用 MIT；基准数据采用 CC BY 4.0（自造集）/ 遵循 C-Eval 原许可（公开集）。
