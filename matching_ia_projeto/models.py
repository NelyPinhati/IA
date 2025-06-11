from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, Text, Float

Base = declarative_base()

class Analise(Base):
    __tablename__ = "analises"
    id = Column(Integer, primary_key=True)
    vaga = Column(Text)
    curriculo = Column(Text)
    score = Column(Float)
    explicacoes = Column(Text)
