"""
test_model_quality.py

Testes de qualidade sobre o modelo já treinado (ml-service/modelo_fraude.pkl),
avaliado no MESMO split de teste reconstruído por train_model.py (seed=42,
train_test_split estratificado) — reaproveitando _common.py, o mesmo padrão
já usado em tune_threshold.py / investigate_fn.py.

Rodar:
    pytest tests/model/test_model_quality.py -v
"""

import json
from pathlib import Path

import pytest

from _common import carregar_e_avaliar

BASELINE_PATH = Path(__file__).resolve().parent / "baseline_metricas.json"

ACURACIA_MINIMA = 0.90
RECALL_MINIMO = 0.40
PRECISAO_MINIMA = 0.70
QUEDA_MAXIMA_PP = 0.05  # 5 pontos percentuais (em escala 0-1)


@pytest.fixture(scope="module")
def metricas() -> dict:
    return carregar_e_avaliar()


@pytest.fixture(scope="module")
def baseline() -> dict:
    assert BASELINE_PATH.exists(), (
        f"Baseline não encontrado em {BASELINE_PATH}. "
        "Rode generate_baseline.py primeiro (uma vez, deliberadamente)."
    )
    return json.loads(BASELINE_PATH.read_text())


def test_acuracia_minima(metricas: dict):
    assert metricas["acuracia"] >= ACURACIA_MINIMA, (
        f"Acurácia {metricas['acuracia']:.4f} abaixo do mínimo aceitável {ACURACIA_MINIMA}"
    )


def test_recall_minimo(metricas: dict):
    assert metricas["recall"] >= RECALL_MINIMO, (
        f"Recall {metricas['recall']:.4f} abaixo do mínimo aceitável {RECALL_MINIMO} "
        "(limitação conhecida documentada em model_card.md: recall=0.50 é aceito)"
    )


def test_precisao_minima(metricas: dict):
    assert metricas["precisao"] >= PRECISAO_MINIMA, (
        f"Precisão {metricas['precisao']:.4f} abaixo do mínimo aceitável {PRECISAO_MINIMA}"
    )


def test_matriz_confusao_soma_bate_com_total(metricas: dict):
    # Sanity check estrutural — não valida valores exatos, só que a matriz é
    # internamente consistente com o tamanho real do conjunto de teste.
    matriz = metricas["matriz_confusao"]
    soma = sum(sum(linha) for linha in matriz)
    assert soma == metricas["n_teste"], (
        f"Soma da matriz de confusão ({soma}) não bate com n_teste ({metricas['n_teste']})"
    )


def test_regressao_contra_baseline(metricas: dict, baseline: dict):
    quedas = {}
    for chave in ("acuracia", "precisao", "recall", "f1"):
        queda = baseline[chave] - metricas[chave]
        if queda > QUEDA_MAXIMA_PP:
            quedas[chave] = {
                "baseline": baseline[chave],
                "atual": metricas[chave],
                "queda_pp": round(queda * 100, 2),
            }

    assert not quedas, (
        f"Regressão detectada (queda > {QUEDA_MAXIMA_PP * 100:.0f} pontos percentuais "
        f"em relação ao baseline): {quedas}"
    )