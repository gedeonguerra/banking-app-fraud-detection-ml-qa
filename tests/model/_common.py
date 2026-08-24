"""
_common.py

Reconstrução do split de teste EXATAMENTE como train_model.py faz (mesma
seed=42, mesmo train_test_split estratificado) — mesmo padrão já usado em
ml-service/tune_threshold.py e ml-service/investigate_fn.py. Compartilhado
entre generate_baseline.py e test_model_quality.py para os dois nunca
divergirem silenciosamente.
"""

from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split

SEED = 42

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATASET_PATH = BASE_DIR / "tests" / "data" / "dataset_transacoes.csv"
MODEL_PATH = BASE_DIR / "ml-service" / "modelo_fraude.pkl"


def carregar_e_avaliar() -> dict:
    artefato = joblib.load(MODEL_PATH)
    modelo = artefato["modelo"]
    encoder = artefato["localizacao_encoder"]

    df = pd.read_csv(DATASET_PATH)
    df["localizacao_enc"] = encoder.transform(df["localizacao"])
    X = df[["valor", "horario", "frequencia_usuario", "localizacao_enc"]]
    y = df["rotulo"]

    _, X_test, _, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=SEED
    )

    y_pred = modelo.predict(X_test)

    return {
        "acuracia": float(accuracy_score(y_test, y_pred)),
        "precisao": float(precision_score(y_test, y_pred, zero_division=0)),
        "recall": float(recall_score(y_test, y_pred, zero_division=0)),
        "f1": float(f1_score(y_test, y_pred, zero_division=0)),
        "matriz_confusao": confusion_matrix(y_test, y_pred).tolist(),
        "n_teste": int(len(y_test)),
    }