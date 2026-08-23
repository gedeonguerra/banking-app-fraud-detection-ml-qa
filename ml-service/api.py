"""
api.py

Microserviço FastAPI que expõe o classificador de fraude de demonstração
(ml-service/modelo_fraude.pkl) via HTTP.

Escopo (principio 3 — não inflar): serve o classificador de DEMONSTRAÇÃO já
documentado em model_card.md (RandomForestClassifier, recall=0.50, limitação
conhecida de localização não-relacional ao usuário). Este microserviço não
adiciona capacidade de detecção nova — só expõe o modelo existente via HTTP.

Endpoints:
    GET  /health         -> healthcheck simples (200), para CI/Cypress
                             confirmarem que o serviço subiu antes dos testes.
    POST /predict-fraud   -> recebe uma transação, retorna probabilidade de
                             fraude usando o threshold=0.5 (aceito como final
                             no model_card.md).
"""

from pathlib import Path

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

MODEL_PATH = Path(__file__).resolve().parent / "modelo_fraude.pkl"
THRESHOLD = 0.5  # mesmo threshold aceito como final no model_card.md (seção 3)

app = FastAPI(
    title="Fraud Classifier API (demonstração)",
    description=(
        "Expõe o classificador de fraude de demonstração deste projeto. "
        "Não é um sistema de detecção de fraude em produção — ver "
        "ml-service/model_card.md para métricas e limitações conhecidas."
    ),
)

# Carregado UMA VEZ na inicialização do processo (import do módulo), não a
# cada request. Se o .pkl não existir, falha explicitamente no startup em vez
# de falhar silenciosamente na primeira requisição.
if not MODEL_PATH.exists():
    raise FileNotFoundError(
        f"Modelo não encontrado em {MODEL_PATH}. Rode train_model.py primeiro."
    )

_artefato = joblib.load(MODEL_PATH)
_modelo = _artefato["modelo"]
_encoder = _artefato["localizacao_encoder"]
_localizacoes_conhecidas = set(_encoder.classes_)


class PredictRequest(BaseModel):
    valor: float = Field(..., gt=0, description="Valor da transação, deve ser > 0")
    horario: int = Field(..., ge=0, le=23, description="Hora do dia, 0-23")
    # Não havia restrição explícita no pedido para frequencia_usuario; ge=0
    # aplicado como validação mínima de sanidade (não pode ser negativa).
    frequencia_usuario: int = Field(..., ge=0, description="Nº de transações do usuário nos últimos 30 dias")
    localizacao: str = Field(..., min_length=1, description="Cidade da transação")


class PredictResponse(BaseModel):
    fraude_provavel: bool
    probabilidade: float
    threshold_usado: float


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/predict-fraud", response_model=PredictResponse)
def predict_fraud(payload: PredictRequest):
    # Limitação conhecida (já registrada em model_card.md, seção 4): o
    # LabelEncoder só conhece as ~50 cidades do dataset sintético de treino.
    # Uma cidade fora desse conjunto quebraria encoder.transform() com
    # ValueError não tratado. Decisão: falhar explicitamente com 422 em vez
    # de mascarar com um fallback silencioso (ex. mapear para código 0), que
    # geraria uma predição sem base real e violaria o principio de não
    # inflar o que o modelo realmente sabe fazer.
    if payload.localizacao not in _localizacoes_conhecidas:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Localização '{payload.localizacao}' não está entre as cidades "
                "vistas no treino do modelo (limitação conhecida — ver "
                "model_card.md, seção 4: LabelEncoder não generaliza para "
                "cidades fora do conjunto de treino). Predição não pode ser "
                "feita com confiabilidade para esta localização."
            ),
        )

    localizacao_enc = _encoder.transform([payload.localizacao])[0]

    linha = pd.DataFrame(
        [
            {
                "valor": payload.valor,
                "horario": payload.horario,
                "frequencia_usuario": payload.frequencia_usuario,
                "localizacao_enc": localizacao_enc,
            }
        ]
    )

    probabilidade = float(_modelo.predict_proba(linha)[0, 1])
    fraude_provavel = probabilidade >= THRESHOLD

    return PredictResponse(
        fraude_provavel=fraude_provavel,
        probabilidade=round(probabilidade, 4),
        threshold_usado=THRESHOLD,
    )