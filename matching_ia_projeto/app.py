from flask import Flask, render_template, request, send_file
from matching import calcular_matching
from models import Analise, Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import fitz  # PyMuPDF
import docx
import re

app = Flask(__name__)

# Banco de dados
engine = create_engine("sqlite:///analises.db")
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# Funções utilitárias para leitura de arquivos
def extrair_texto_pdf(path):
    texto = ""
    with fitz.open(path) as doc:
        for page in doc:
            texto += page.get_text()
    return texto.strip()

def extrair_texto_docx(path):
    texto = ""
    doc = docx.Document(path)
    for p in doc.paragraphs:
        texto += p.text + "\n"
    return texto.strip()

def extrair_palavras_chave(texto):
    """Extrai palavras-chave relevantes de um texto, ignorando stopwords."""
    stopwords = set([
        "de", "da", "do", "e", "a", "o", "as", "os", "em", "para", "com", "por", "um", "uma", "na", "no", "que", "é", "ser", "ou", "dos", "das"
        # Adicione mais stopwords conforme necessário
    ])
    palavras = re.findall(r'\b\w{3,}\b', texto.lower())
    palavras_chave = [p for p in palavras if p not in stopwords]
    return list(set(palavras_chave))

# Página principal
@app.route("/", methods=["GET", "POST"])
def index():
    resultados = []
    if request.method == "POST":
        vaga_texto = request.form.get("vaga_texto", "")
        cv_texto = request.form.get("cv_texto", "")

        vaga_files = request.files.getlist('vaga_file')
        cv_files = request.files.getlist('cv_file')

        # Processa cada vaga
        for vaga_file in vaga_files if vaga_files else [None]:
            if vaga_file and vaga_file.filename:
                ext_vaga = vaga_file.filename.split(".")[-1].lower()
                path_vaga = "temp_vaga." + ext_vaga
                vaga_file.save(path_vaga)
                vaga_texto_atual = extrair_texto_pdf(path_vaga) if ext_vaga == "pdf" else extrair_texto_docx(path_vaga)
                vaga_nome = vaga_file.filename
            else:
                vaga_texto_atual = vaga_texto  # Se não enviou arquivo, usa texto digitado
                vaga_nome = "Texto digitado"

            # Processa cada currículo para cada vaga
            for cv_file in cv_files if cv_files else [None]:
                if cv_file and cv_file.filename:
                    ext_cv = cv_file.filename.split(".")[-1].lower()
                    path_cv = "temp_cv." + ext_cv
                    cv_file.save(path_cv)
                    if os.path.getsize(path_cv) > 0:
                        cv_texto_atual = extrair_texto_pdf(path_cv) if ext_cv == "pdf" else extrair_texto_docx(path_cv)
                        cv_nome = cv_file.filename
                    else:
                        cv_texto_atual = ""
                        cv_nome = "Arquivo vazio"
                else:
                    cv_texto_atual = cv_texto  # Se não enviou arquivo, usa texto digitado
                    cv_nome = "Texto digitado"

                # Extração de palavras-chave
                palavras_chave_vaga = extrair_palavras_chave(vaga_texto_atual)
                palavras_chave_cv = extrair_palavras_chave(cv_texto_atual)

                # Score: % de palavras-chave da vaga presentes no CV
                palavras_encontradas = [p for p in palavras_chave_vaga if p in palavras_chave_cv]
                palavras_nao_encontradas = [p for p in palavras_chave_vaga if p not in palavras_chave_cv]
                score = round(len(palavras_encontradas) / len(palavras_chave_vaga) * 100, 2) if palavras_chave_vaga else 0

                explicacoes = [
                    f"Palavras-chave da vaga: {', '.join(palavras_chave_vaga)}",
                    f"Palavras-chave encontradas no CV: {', '.join(palavras_encontradas)}",
                    f"Palavras-chave não encontradas: {', '.join(palavras_nao_encontradas)}"
                ]

                session = Session()
                analise = Analise(
                    vaga=vaga_texto_atual,
                    curriculo=cv_texto_atual,
                    score=score,
                    explicacoes="\n".join(explicacoes)
                )
                session.add(analise)
                session.commit()
                resultados.append({
                    "score": score,
                    "explicacoes": explicacoes,
                    "id": analise.id,
                    "vaga_texto": vaga_texto_atual,
                    "cv_texto": cv_texto_atual,
                    "vaga_nome": vaga_nome,
                    "cv_nome": cv_nome,
                    "gaps": palavras_nao_encontradas
                })

    return render_template("index.html", resultados=resultados)

# Geração de PDF com logo e explicações
@app.route("/relatorio/<int:analise_id>")
def relatorio(analise_id):
    session = Session()
    analise = session.query(Analise).get(analise_id)
    if not analise:
        return "Relatório não encontrado", 404

    pdf_path = f"relatorio_{analise_id}.pdf"
    c = canvas.Canvas(pdf_path, pagesize=A4)

    # Inserir logo (ajuste o caminho se necessário)
    logo_path = os.path.join("static", "logo.png")
    if os.path.exists(logo_path):
        logo = ImageReader(logo_path)
        c.drawImage(logo, 40, 770, width=100, height=50)

    c.setFont("Helvetica-Bold", 16)
    c.drawString(150, 800, "Relatório de Matching IA")

    c.setFont("Helvetica", 12)
    c.drawString(40, 740, f"Score de Aderência: {analise.score}%")

    c.drawString(40, 720, "Explicações:")
    y = 700
    max_chars = 90  # número máximo de caracteres por linha

    for linha in analise.explicacoes.splitlines():
        palavras = linha.split()
        linha_atual = "- "
        for palavra in palavras:
            if len(linha_atual) + len(palavra) + 1 > max_chars:
                c.drawString(60, y, linha_atual)
                y -= 20
                if y < 50:
                    c.showPage()
                    y = 800
                linha_atual = "  " + palavra + " "
            else:
                linha_atual += palavra + " "
        if linha_atual.strip():
            c.drawString(60, y, linha_atual)
            y -= 20
            if y < 50:
                c.showPage()
                y = 800

    c.showPage()
    c.save()
    return send_file(pdf_path, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
    
    
