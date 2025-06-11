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


# Página principal
@app.route("/", methods=["GET", "POST"])
def index():
    resultado = None

    if request.method == "POST":
        vaga_texto = request.form.get("vaga_texto", "")
        cv_texto = request.form.get("cv_texto", "")

        vaga_file = request.files.get("vaga_file")
        cv_file = request.files.get("cv_file")

        if vaga_file and vaga_file.filename:
            ext = vaga_file.filename.split(".")[-1].lower()
            path = "temp_vaga." + ext
            vaga_file.save(path)
            vaga_texto = extrair_texto_pdf(path) if ext == "pdf" else extrair_texto_docx(path)

        if cv_file and cv_file.filename:
            ext = cv_file.filename.split(".")[-1].lower()
            path = "temp_cv." + ext
            cv_file.save(path)
            cv_texto = extrair_texto_pdf(path) if ext == "pdf" else extrair_texto_docx(path)

        score, explicacoes = calcular_matching(cv_texto, vaga_texto)

        session = Session()
        analise = Analise(
            vaga=vaga_texto,
            curriculo=cv_texto,
            score=score,
            explicacoes="\n".join(explicacoes)
        )
        session.add(analise)
        session.commit()

        resultado = {
            "score": score,
            "explicacoes": explicacoes,
            "id": analise.id,
            "vaga_texto": vaga_texto,
            "cv_texto": cv_texto
        }

    return render_template("index.html", resultado=resultado)


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
    for linha in analise.explicacoes.splitlines():
        if y < 50:
            c.showPage()
            y = 800
        c.drawString(60, y, f"- {linha}")
        y -= 20

    c.showPage()
    c.save()

    return send_file(pdf_path, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True)
