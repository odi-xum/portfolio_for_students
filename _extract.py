"""Extract text from the reference thesis DOCX."""
import docx
doc = docx.Document('/home/odi/Documents/projects/diplom/Diplom_Shvetsov_I_G (1).docx')
for i, p in enumerate(doc.paragraphs, 1):
    text = p.text.strip()
    style = p.style.name
    if text:
        print(f'[{i}][{style}] {text}')
