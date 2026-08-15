# -*- coding: utf-8 -*-
"""仅处理完整实验记录：基于已含 #25 的 _补25.docx，复制到临时不被占文件做补丁，
再覆盖回原名（完成此前被锁中断的覆盖 + 加 C-Eval 对照真实结果）。
可视化报告已在上一轮成功补丁，本脚本不重复处理。
"""
import zipfile, shutil, re, os

def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def para(text, bold=False):
    rpr = '<w:rPr><w:b/></w:rPr>' if bold else ''
    return f'<w:p><w:pPr></w:pPr><w:r>{rpr}<w:t xml:space="preserve">{esc(text)}</w:t></w:r></w:p>'

CTRL_BLOCK = [
    para("【2026-08-12 补充】容量/语言对照（原 #21/#22 记为“排队待跑”）已于今日实际跑完（产物 stage2_ceval_ctrl_cap_k1.json / stage2_ceval_ctrl_lang_k1.json，status=done）。", bold=True),
    para("• 容量对照（#21）：L3/聚合/L2 由 1.5B 升到 3B，主脑 7B，k=1，中文 C-Eval（ceval_bandok_clean, n=200）。集体=0.720，最强单体(7B)=0.785，committee0(L3 3B 投票)=0.68。仍无涌现（0.720<0.785），但比原 1.5B 集体 0.66 升 +6pp → 下层容量提升有帮助，仍未涌现。"),
    para("• 语言对照（#22）：同题翻译英文 C-Eval（ceval_en.jsonl，7B 翻译生成），默认 1.5B×k，k=1。集体=0.585，最强单体(7B)=0.675。仍无涌现且比中文 0.66 更低。"),
    para("• 解读（支持用户 8-11 00:50 互补结构假说）：两对照坐实“涌现=架构×下层相对顶层互补信号盈余；顶层占优+下层只添噪声→回归均值涌现归零”。容量对照排除“下层完全无能力”（3B 更强→集体更高）仍未涌现→7B 信息最全层，下层只添弱信号；语言对照换同题英文也掉分→坐实难度/互补结构非语言特定弱点（朴素“看不懂”版已驳）。英文版更低(0.585<0.66)部分因 7B 英文单体也降到 0.675（翻译损失/英文更难），干净分离待回译检查或密度扫描后独占重跑。"),
]
CTRL_XML = ''.join(CTRL_BLOCK)

def patch(path, anchor):
    z = zipfile.ZipFile(path)
    xml = z.read('word/document.xml').decode('utf-8')
    parts = xml.split('</w:p>')
    inserted = False
    for i, p in enumerate(parts):
        txt = re.sub(r'<[^>]+>', '', p)
        if anchor in txt and not inserted:
            before = '</w:p>'.join(parts[:i + 1]) + '</w:p>'
            after = '</w:p>'.join(parts[i + 1:])
            new_xml = before + CTRL_XML + after
            inserted = True
            break
    if not inserted:
        raise SystemExit(f"ANCHOR NOT FOUND: {anchor} in {path}")
    tmp = path + '.tmp'
    with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
        for item in z.infolist():
            data = z.read(item.filename)
            if item.filename == 'word/document.xml':
                data = new_xml.encode('utf-8')
            zout.writestr(item, data)
    shutil.move(tmp, path)
    print(f"[ok] patched {path} (anchor='{anchor}')")

REC_BASE = "D:/方程验证/完整实验记录_2026-08-11/完整实验记录_2026-08-11_补25.docx"
REC_ORIG = "D:/方程验证/完整实验记录_2026-08-11/完整实验记录_2026-08-11.docx"
TMP_BASE = "D:/方程验证/_rec_ctrl_base.docx"

# _补25.docx 被某进程占用，无法直接原地写；先复制到不受占的临时文件再补丁
if os.path.exists(TMP_BASE):
    os.remove(TMP_BASE)
shutil.copy(REC_BASE, TMP_BASE)   # 读 REC_BASE（共享读），写新文件
patch(TMP_BASE, "互补门控")
shutil.copy(TMP_BASE, REC_ORIG)   # 覆盖原名（原名当前不被占）
os.remove(TMP_BASE)
print(f"[ok] REC: patched via tmp, copied -> {REC_ORIG}")
