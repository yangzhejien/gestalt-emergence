import shutil, os
import docx

SRC = "D:/方程验证/完整实验记录_2026-08-11/完整实验记录_2026-08-11_含对照.docx"
BAK = SRC + ".bak_p13"
shutil.copy(SRC, BAK)

d = docx.Document(SRC)
# 找到含 P12 的表
target = None
for t in d.tables:
    if any("P12" in c.text for r in t.rows for c in r.cells):
        target = t
        break
assert target is not None, "未找到事故表"

# 加一行 (python-docx 复制末行样式)
row = target.add_row()
cells = row.cells
cells[0].text = "P13"
cells[1].text = "密度扫描 k>7 FATAL 崩溃（persona 不足 + 休眠带停 Ollama）（08-13 事故）"
cells[2].text = ("verify_stage2.py 中 l3_personas 仅 7 个独立专家视角，密度扫描扫 k=8/10/12/15/20 时用 [:k] 截断"
                 "→k=8 仅生成 l3_0..l3_6，第 8 个专家 l3_7 从未生成；后续 committee0 多数投票访问 solos['l3_7']"
                 "→KeyError:'l3_7'→FATAL；监督重试 60 次无效；叠加电脑休眠把 Ollama 服务带停（WinError 10061），"
                 "k8 停滞 ~6.5h（07:14→13:49 才发现）。修复：①persona 循环复用（i%len，k>7 轮转）"
                 "② solo 基线+集体路径两处 [:k] 截断均改 ③committee0 加 try/except 防御（不再 FATAL）"
                 "④py_compile 通过 ⑤沙箱 ollama serve 拉起（alive:200）⑥编排器重启 13:57 正常推进"
                 "（Solo L3-1/8 q40/500，8 专家齐全）")
cells[3].text = ("暴露并修复 k>7 必崩的确定性 bug，证明密度扫描对 persona 数量敏感；"
                 "强化「所有 k 档必须 persona 充足」复现要求；"
                 "与 P12（max_tokens）并列构成密度扫描的两道前置修复")

d.save(SRC)
print("OK saved. table rows now:", len(target.rows))
print("last row:", [c.text[:30] for c in target.rows[-1].cells])
