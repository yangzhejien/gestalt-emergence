import zipfile
from xml.etree import ElementTree as ET
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
p = r'D:/cdb1c5f4ed8f5d6a76dc77efce4bfe68 (1).docx'
z = zipfile.ZipFile(p)
root = ET.fromstring(z.read('word/document.xml'))
paras = []
for para in root.iter(W + 'p'):
    txt = ''.join(t.text or '' for t in para.iter(W + 't'))
    paras.append(txt)
out = '\n'.join(paras)
out_path = r'D:/方程验证/scripts/_docx_extract.txt'
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(out)
print('chars:', len(out))
print('paras:', len(paras))
