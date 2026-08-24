"""
test_dataset_quality.py

Testes de qualidade de dados sobre tests/data/dataset_transacoes.csv
(Fase 3.1 — base da pirâmide de testes: QA de dados).

Decisão de ferramenta (pytest puro, não Great Expectations):
    Great Expectations exige DataContext, expectation suites e checkpoints —
    infraestrutura própria de configuração e armazenamento desproporcional
    para validar 7 propriedades simples sobre um único CSV estático, no
    escopo de demonstração/QA deste projeto. pytest + asserções pandas
    entregam o mesmo rigor de validação com muito menos complexidade e sem
    adicionar uma dependência pesada nova nesta fase. Se o projeto evoluir
    para múltiplas fontes de dados versionadas/pipelines de dados
    recorrentes, Great Expectations passaria a valer a pena — não é o caso
    hoje.

Rodar:
    pytest tests/data/test_dataset_quality.py -v
"""

from pathlib import Path

import pandas as pd
import pytest

DATASET_PATH = Path(__file__).resolve().parent / "dataset_transacoes.csv"

TAXA_FRAUDE_MIN = 0.01  # 1%
TAXA_FRAUDE_MAX = 0.06  # 6% — faixa de tolerância em torno dos ~3% esperados


@pytest.fixture(scope="module")
def df() -> pd.DataFrame:
    assert DATASET_PATH.exists(), f"Dataset não encontrado em {DATASET_PATH}"
    return pd.read_csv(DATASET_PATH)


def test_sem_valores_nulos(df: pd.DataFrame):
    nulos = df.isnull().sum()
    assert nulos.sum() == 0, f"Valores nulos encontrados por coluna:\n{nulos[nulos > 0]}"


def test_valor_maior_que_zero(df: pd.DataFrame):
    invalidos = df[df["valor"] <= 0]
    assert invalidos.empty, f"{len(invalidos)} linha(s) com valor <= 0"


def test_horario_entre_0_e_23(df: pd.DataFrame):
    invalidos = df[(df["horario"] < 0) | (df["horario"] > 23)]
    assert invalidos.empty, f"{len(invalidos)} linha(s) com horario fora de 0-23"


def test_frequencia_usuario_maior_ou_igual_a_1(df: pd.DataFrame):
    invalidos = df[df["frequencia_usuario"] < 1]
    assert invalidos.empty, f"{len(invalidos)} linha(s) com frequencia_usuario < 1"


def test_rotulo_apenas_0_ou_1(df: pd.DataFrame):
    valores_unicos = set(df["rotulo"].unique())
    assert valores_unicos.issubset({0, 1}), f"Valores inesperados em rotulo: {valores_unicos - {0, 1}}"


def test_taxa_de_fraude_dentro_da_faixa_esperada(df: pd.DataFrame):
    taxa = (df["rotulo"] == 1).mean()
    assert TAXA_FRAUDE_MIN <= taxa <= TAXA_FRAUDE_MAX, (
        f"Taxa de fraude {taxa:.4f} fora da faixa esperada "
        f"[{TAXA_FRAUDE_MIN}, {TAXA_FRAUDE_MAX}]"
    )


def test_localizacao_nao_vazia(df: pd.DataFrame):
    vazios = df[df["localizacao"].isna() | (df["localizacao"].astype(str).str.strip() == "")]
    assert vazios.empty, f"{len(vazios)} linha(s) com localizacao vazia"