import fitz  # PyMuPDF
import docx
import tempfile

def extrair_texto_pdf_docx(file_storage):
    filename = file_storage.filename.lower()
    if filename.endswith(".pdf"):
        return extrair_texto_pdf(file_storage)
    elif filename.endswith(".docx"):
        return extrair_texto_docx(file_storage)
    else:
        return ""

def extrair_texto_pdf(file_storage):
    texto = ""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        file_storage.save(tmp.name)
        doc = fitz.open(tmp.name)
        for page in doc:
            texto += page.get_text()
        doc.close()
    return texto

def extrair_texto_docx(file_storage):
    texto = ""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
        file_storage.save(tmp.name)
        doc = docx.Document(tmp.name)
        for para in doc.paragraphs:
            texto += para.text + "\n"
    return texto
