"""
test_predict_fraud_contract.py

Testes de contrato da API de predição de fraude (ml-service/api.py), via
fastapi.testclient.TestClient — mesma ferramenta e mesmo limite já declarados
na Fase 2.3: transporte ASGI in-process, sem socket real, sem uvicorn
rodando. Não substitui validação HTTP real ponta a ponta.

Rodar:
    pytest tests/api/test_predict_fraud_contract.py -v
"""

import sys
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR / "ml-service"))

from api import app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

client = TestClient(app)

# Cidade real do dataset sintético (mesma usada na investigação de falsos
# negativos, Fase 2.2 — já confirmada como conhecida pelo LabelEncoder).
CIDADE_CONHECIDA = "Daviston"

PAYLOAD_VALIDO = {
    "valor": 150.0,
    "horario": 14,
    "frequencia_usuario": 8,
    "localizacao": CIDADE_CONHECIDA,
}


def test_health_retorna_200_status_ok():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_predict_fraud_payload_valido_schema_e_tipos():
    r = client.post("/predict-fraud", json=PAYLOAD_VALIDO)
    assert r.status_code == 200

    body = r.json()
    assert set(body.keys()) == {"fraude_provavel", "probabilidade", "threshold_usado"}

    assert isinstance(body["fraude_provavel"], bool)
    assert isinstance(body["probabilidade"], float)
    assert isinstance(body["threshold_usado"], float)


def test_probabilidade_entre_0_e_1():
    r = client.post("/predict-fraud", json=PAYLOAD_VALIDO)
    assert r.status_code == 200
    probabilidade = r.json()["probabilidade"]
    assert 0.0 <= probabilidade <= 1.0


def test_threshold_usado_e_sempre_0_5():
    r = client.post("/predict-fraud", json=PAYLOAD_VALIDO)
    assert r.status_code == 200
    assert r.json()["threshold_usado"] == 0.5


def test_localizacao_desconhecida_retorna_422():
    payload = {**PAYLOAD_VALIDO, "localizacao": "CidadeQueNaoExisteNoTreino"}
    r = client.post("/predict-fraud", json=payload)
    assert r.status_code == 422


@pytest.mark.parametrize("horario_invalido", [-1, 24, 100])
def test_horario_fora_de_0_23_retorna_422(horario_invalido):
    payload = {**PAYLOAD_VALIDO, "horario": horario_invalido}
    r = client.post("/predict-fraud", json=payload)
    assert r.status_code == 422


@pytest.mark.parametrize("valor_invalido", [0, -10.0])
def test_valor_menor_ou_igual_a_zero_retorna_422(valor_invalido):
    payload = {**PAYLOAD_VALIDO, "valor": valor_invalido}
    r = client.post("/predict-fraud", json=payload)
    assert r.status_code == 422


def test_campo_obrigatorio_faltando_retorna_422():
    payload = {k: v for k, v in PAYLOAD_VALIDO.items() if k != "valor"}
    r = client.post("/predict-fraud", json=payload)
    assert r.status_code == 422


def test_tipo_errado_retorna_422():
    payload = {**PAYLOAD_VALIDO, "valor": "abc"}
    r = client.post("/predict-fraud", json=payload)
    assert r.status_code == 422