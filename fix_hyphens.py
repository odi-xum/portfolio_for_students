#!/usr/bin/env python3
"""Replace hyphen list markers with em-dash in the diploma DOCX."""

import zipfile, shutil, os, re
from xml.etree import ElementTree as ET

src = '/home/odi/Documents/projects/diplom/Дипломная_работа_Мелехов_АК.docx'
tmp = '/tmp/diploma_fixed2.docx'
shutil.copy2(src, tmp)

with zipfile.ZipFile(tmp, 'r') as zin:
    raw = zin.read('word/document.xml')

root = ET.fromstring(raw)
changes = 0

for t in root.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'):
    if not t.text:
        continue
    if t.text.startswith('- ') and (len(t.text) == 2 or t.text[2] != '—'):
        old = t.text
        t.text = '— ' + t.text[2:]
        changes += 1

for p in root.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p'):
    for t in p.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'):
        if t.text and t.text.strip() and t.text.startswith('- '):
            if t.text.startswith('—'):
                continue
            old = t.text
            t.text = '— ' + t.text[2:]
            changes += 1
            break

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

print(f'Done. {changes} replacements made.')
print(f'File: {src} ({os.path.getsize(src)} bytes)')
