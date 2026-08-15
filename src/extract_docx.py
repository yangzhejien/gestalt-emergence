import zipfile, re, sys

src = r'D:\cdb1c5f4ed8f5d6a76dc77efce4bfe68 (1).docx'
z = zipfile.ZipFile(src)
xml = z.read('word/document.xml').decode('utf-8', errors='ignore')

# extract text from <w:t> tags
texts = re.findall(r'<w:t[^>]*>(.*?)</w:t>', xml, re.DOTALL)
# unescape
def unesc(s):
    s = s.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    s = s.replace('&quot;', '"').replace('&apos;', "'")
    return s

paras = re.split(r'</w:p>', xml)
out = []
for p in paras:
    ts = re.findall(r'<w:t[^>]*>(.*?)</w:t>', p, re.DOTALL)
    line = ''.join(unesc(t) for t in ts)
    out.append(line)

full = '\n'.join(out)
open(r'D:\方程验证\docx_extracted.txt', 'w', encoding='utf-8').write(full)
print('CHARS:', len(full))
print('=' * 60)
print(full[:6000])
