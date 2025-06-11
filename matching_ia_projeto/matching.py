from sentence_transformers import SentenceTransformer, util

model = SentenceTransformer("all-MiniLM-L6-v2")

def calcular_matching(cv_texto, vaga_texto):
    cv_embedding = model.encode(cv_texto, convert_to_tensor=True)
    vaga_embedding = model.encode(vaga_texto, convert_to_tensor=True)

    score = util.cos_sim(cv_embedding, vaga_embedding).item() * 100

    explicacao = []
    if "Python" in cv_texto and "Python" in vaga_texto:
        explicacao.append("Possui habilidade em Python.")
    if "AWS" in cv_texto and "AWS" in vaga_texto:
        explicacao.append("Experiência com AWS detectada.")
    if "liderança" in cv_texto.lower():
        explicacao.append("Candidato demonstra perfil de liderança.")
    if "projetos" in cv_texto.lower():
        explicacao.append("Experiência em gestão ou participação de projetos.")

    return round(score, 2), explicacao
