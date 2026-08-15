import re

src = r'D:\方程验证\OSF_preregistration_2026-08-07.md'
out = r'D:\方程验证\OSF_preregistration_2026-08-07.html'

MATH_RE = re.compile(r'(\$\$.+?\$\$|\$.+?\$)', re.DOTALL)

def escape_and_style(s):
    s = s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
    s = re.sub(r'`(.+?)`', r'<code>\1</code>', s)
    return s

def process_inline(s):
    out_parts = []
    pos = 0
    for m in MATH_RE.finditer(s):
        out_parts.append(escape_and_style(s[pos:m.start()]))
        out_parts.append(m.group(0))  # raw math for MathJax
        pos = m.end()
    out_parts.append(escape_and_style(s[pos:]))
    return ''.join(out_parts)

def render_table(rows):
    def cells(r):
        r = r.strip()
        if r.startswith('|'): r = r[1:]
        if r.endswith('|'): r = r[:-1]
        return [process_inline(c.strip()) for c in r.split('|')]
    out_parts = ['<table>']
    for idx, r in enumerate(rows):
        stripped = r.replace('|', '').replace('-', '').replace(' ', '')
        if stripped == '' and '-' in r:
            continue
        cs = cells(r)
        if idx == 0:
            th = ''.join(f'<th>{c}</th>' for c in cs)
            out_parts.append(f'<thead><tr>{th}</tr></thead><tbody>')
        else:
            td = ''.join(f'<td>{c}</td>' for c in cs)
            out_parts.append(f'<tr>{td}</tr>')
    out_parts.append('</tbody></table>')
    return ''.join(out_parts)

head = (
'<html><head><meta charset="utf-8"><title>OSF Preregistration — Gestalt Equation</title>\n'
'<script>\n'
'  MathJax = { tex: { inlineMath: [[\'$\', \'$\']], displayMath: [[\'$$\', \'$$\']] }, svg: { fontCache: \'global\' } };\n'
'</script>\n'
'<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js" async></script>\n'
'<style>\n'
'body{font-family:system-ui,\'Segoe UI\',Arial,sans-serif;max-width:920px;margin:40px auto;padding:0 24px;line-height:1.65;color:#1a2027;background:#fff;}\n'
'h1{font-size:24px;border-bottom:3px solid #2563eb;padding-bottom:8px;}\n'
'h2{font-size:19px;color:#1d4ed8;margin-top:28px;}\n'
'h3{font-size:16px;color:#374151;margin-top:20px;}\n'
'blockquote{background:#f1f5f9;border-left:4px solid #2563eb;margin:12px 0;padding:8px 16px;color:#334155;}\n'
'code{background:#f1f5f9;padding:1px 5px;border-radius:3px;font-size:13px;}\n'
'ul{margin:8px 0;padding-left:24px;}\n'
'li{margin:4px 0;}\n'
'table{border-collapse:collapse;margin:14px 0;width:100%;font-size:14px;}\n'
'th,td{border:1px solid #cbd5e1;padding:7px 10px;text-align:left;vertical-align:top;}\n'
'th{background:#e2e8f0;font-weight:600;}\n'
'tbody tr:nth-child(even){background:#f8fafc;}\n'
'.note{background:#fffbeb;border:1px solid #fcd34d;padding:12px 16px;border-radius:6px;color:#92400e;margin:16px 0;}\n'
'.MathJax_Display{margin:6px 0;}\n'
'</style></head><body>'
)

html = [head]
html.append('<div class="note"><strong>说明：</strong>作者名已填（杨智杰 / Yang Zhijie）。方程现已用 LaTeX 渲染（预览需联网加载 MathJax；上传 OSF 后由 OSF 原生渲染）。本预览含完整的方程推导（§4，整合自作者 v1.2.0 草稿并经实验数据修正）。下一步：上传到 osf.io 并 <strong>Make Public</strong> 即可锁定时间戳。无需 Word / 付费软件。</div>')

md = open(src, encoding='utf-8').read()
lines = md.split('\n')

i = 0
list_open = False
while i < len(lines):
    line = lines[i]
    stripped = line.strip()
    if line.startswith('# '):
        if list_open: html.append('</ul>'); list_open = False
        html.append(f'<h1>{process_inline(line[2:])}</h1>')
    elif line.startswith('## '):
        if list_open: html.append('</ul>'); list_open = False
        html.append(f'<h2>{process_inline(line[3:])}</h2>')
    elif line.startswith('### '):
        if list_open: html.append('</ul>'); list_open = False
        html.append(f'<h3>{process_inline(line[4:])}</h3>')
    elif line.startswith('> '):
        if list_open: html.append('</ul>'); list_open = False
        html.append(f'<blockquote>{process_inline(line[2:])}</blockquote>')
    elif stripped.startswith('|'):
        tbl = [line]
        j = i + 1
        while j < len(lines) and lines[j].strip().startswith('|'):
            tbl.append(lines[j]); j += 1
        if list_open: html.append('</ul>'); list_open = False
        html.append(render_table(tbl))
        i = j
        continue
    elif line.startswith('- '):
        if not list_open: html.append('<ul>'); list_open = True
        html.append(f'<li>{process_inline(line[2:])}</li>')
    elif stripped == '':
        if list_open: html.append('</ul>'); list_open = False
    else:
        if list_open: html.append('</ul>'); list_open = False
        html.append(f'<p>{process_inline(line)}</p>')
    i += 1
if list_open: html.append('</ul>')
html.append('</body></html>')

open(out, 'w', encoding='utf-8').write('\n'.join(html))
print('saved', out)
