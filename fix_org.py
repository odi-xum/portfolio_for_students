#!/usr/bin/env python3
"""Fix the organization name in the diploma DOCX."""

import zipfile, shutil, os
from xml.etree import ElementTree as ET

src = '/home/odi/Documents/projects/diplom/Дипломная_работа_Мелехов_АК.docx'
tmp = '/tmp/diploma_fixed.docx'
shutil.copy2(src, tmp)

with zipfile.ZipFile(tmp, 'r') as zin:
    raw = zin.read('word/document.xml')

root = ET.fromstring(raw)
changes = 0

for t in root.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'):
    if not t.text:
        continue
    old = t.text
    new = old
    new = new.replace('Автономное учреждение профессионального образования', 'Автономное учреждение')
    new = new.replace('автономного учреждения профессионального образования', 'автономного учреждения')
    new = new.replace('АУ ПО «ХМТПК»', 'АУ «ХМТПК»')
    if new != old:
        t.text = new
        changes += 1
        print(f'  {old} -> {new}')

new_xml = ET.tostring(root, encoding='unicode', xml_declaration=False)

with zipfile.ZipFile(tmp, 'r') as zin:
    all_files = {}
    for name in zin.namelist():
        data = zin.read(name)
        if name == 'word/document.xml':
            data = new_xml.encode('utf-8')
        all_files[name] = data

with zipfile.ZipFile(src, 'w', zipfile.ZIP_DEFLATED) as zout:
    for name, data in all_files.items():
        zout.writestr(name, data)

print(f'\nDone. {changes} replacements made.')
print(f'File: {src} ({os.path.getsize(src)} bytes)')
