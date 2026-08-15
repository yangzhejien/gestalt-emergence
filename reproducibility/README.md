# 方程验证 (Gestalt Equation Verification)

格式塔方程的**专用验证工程**,独立于 SFT 数据集与推导文档。

## 目标(本阶段)
验证方程头部的**二次项 → 四次项**:
```
G(Ẇ) ≈ α1 · Ẇ² + α2 · Ẇ⁴
```
即证明"连接强度产生偶次幂涌现增益"这一核心机制可行、可拟合。
更高阶(Ẇ⁶ 及临界点 Ẇ_c)留待后续批次。

## 目录结构
```
方程验证/
├── scripts/verify_head.py     # 验证脚手架(同质 1.5b×k 节点)
├── configs/verify_config.json # 节点数/人格/w 档/基准等参数
├── benchmark/mcq_small.jsonl  # 自包含 MCQ 基准(30题,自动评分)
├── data/                      # 输出的 (Ẇ, G) 数据点 CSV
├── results/                   # 拟合报告 + 判定
├── models/                    # 节点模型说明(见下)
└── README.md
```

## 节点模型
- 主节点基模:**qwen2.5:1.5b**(Ollama 本地,已在底盘)
- Ollama 权重存于 `~/.ollama`,**不复制进本文件夹**(复制会破坏 blob 引用);
  本工程的"模型"指:通过 `verify_config.json` 引用该本地模型 + 3 种 persona 提示,
  构成 k=3 个"同质不同立场"的验证节点。
- 若要做"节点异质性"secondary 实验,可把 `fs-agent-v2`(7B 独立意志体)等
  作为异构节点对照,但主验证坚持同质以隔离拓扑效应。

## 方法(为什么这样测)
1. **Round1**: 每个节点(不同 persona)独立作答 → 节点准确率 a_i
2. **A_net(0)**: 节点独立答案的多数投票 = 委员会基线
3. **Round2(w)**: 每个节点看到其他节点 Round1 答案(按权重 w)→ 修订后多数投票 = A_net(w)
4. **G(w)** = cap(A_net(w)) − cap(A_net(0)),在 **logit 空间**计算
   (cap(p)=logit(p),使能力可加、且 G 可比 Σs_i 大,对应互信息推导)
5. **Ẇ(w)** = 2w (全连接 k 节点, Ẇ = Σw_ij / W_max(k))
6. 拟合 G ≈ α1Ẇ² + α2Ẇ⁴,与线性零模型 G≈βẆ 比 R²,报 α 的 bootstrap 95% CI

## 运行
```bash
# 确保 ollama 已在运行(ollama serve / 桌面客户端)
# 冒烟(快): 5 题
python scripts/verify_head.py --n 5 --w 0,0.5,1.0 --tag smoke
# 正式(慢): 全量 30 题, 5 个 w 档
python scripts/verify_head.py
```
输出:
- `data/verify_data.csv` — (w, Ẇ, A_net0, A_net_w, G)
- `results/verify_report.md` — 拟合系数、R²、CI、判定(★级)

## 判定标准(公开可证伪)
- R²_full > R²_linear 且 α2 的 95% CI 不含 0 → ★★★ 强支持偶次幂(含四次项)
- 仅 α1 显著 → ★★ 仅验证到 Ẇ²
- 否则 → ★/0 需修正

## 与已有资产的衔接
- 完整推导:`格式塔方程_完整推导_v1.4.0.md`
- 数学收紧:`格式塔方程_v1.3.0_数学收紧.md`
- 实验方案:`格式塔方程_实验方案_v1.md`
- 通用拟合:`gestalt_fit.py`(本脚手架自带拟合,亦可用它复算)
