#!/usr/bin/env python3
"""
tune_threshold.py

Reavalia o modelo já treinado (ml-service/modelo_fraude.pkl) usando
predict_proba() em vez de predict(), comparando múltiplos thresholds de
decisão sobre o MESMO split de teste usado em train_model.py (mesma seed,
mesmo train_test_split estratificado — reconstruído aqui, não persistido
separadamente).

Não escolhe "o melhor" threshold automaticamente — reporta todos e deixa a
decisão para orquestrador/usuário, sinalizando o trade-off:
    threshold mais baixo -> recall sobe, precisão cai (mais falsos positivos)
    threshold mais alto  -> precisão sobe, recall cai (mais fraudes não detectadas)

Não retreina o modelo nem altera o .pkl — apenas avalia.
"""

from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split

SEED = 42  # mesma seed usada em train_model.py, necessária para reconstruir o split idêntico

BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_PATH = BASE_DIR / "tests" / "data" / "dataset_transacoes.csv"
MODEL_PATH = Path(__file__).resolve().parent / "modelo_fraude.pkl"

THRESHOLDS = [0.5, 0.4, 0.3, 0.2]


def carregar_modelo(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(
            f"Modelo não encontrado em {path}. Rode train_model.py primeiro."
        )
    return joblib.load(path)


def reconstruir_split_teste(df: pd.DataFrame, encoder) -> tuple[pd.DataFrame, pd.Series]:
    df = df.copy()
    df["localizacao_enc"] = encoder.transform(df["localizacao"])

    X = df[["valor", "horario", "frequencia_usuario", "localizacao_enc"]]
    y = df["rotulo"]

    # mesmos parâmetros de train_model.py -> reproduz o split idêntico
    _, X_test, _, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=SEED
    )
    return X_test, y_test


def avaliar_thresholds(modelo, X_test, y_test, thresholds: list[float]) -> list[dict]:
    probas = modelo.predict_proba(X_test)[:, 1]  # probabilidade da classe "fraude"

    linhas = []
    for t in thresholds:
        y_pred = (probas >= t).astype(int)
        tn, fp, fn, tp = confusion_matrix(y_test, y_pred).ravel()
        linhas.append(
            {
                "threshold": t,
                "precisao": precision_score(y_test, y_pred, zero_division=0),
                "recall": recall_score(y_test, y_pred, zero_division=0),
                "f1": f1_score(y_test, y_pred, zero_division=0),
                "tp": int(tp),
                "fp": int(fp),
                "fn": int(fn),
                "tn": int(tn),
            }
        )
    return linhas


def imprimir_tabela(linhas: list[dict]) -> None:
    header = f"{'threshold':>9} | {'precisao':>8} | {'recall':>7} | {'f1':>6} | {'TP':>3} | {'FP':>3} | {'FN':>3} | {'TN':>4}"
    print(header)
    print("-" * len(header))
    for l in linhas:
        print(
            f"{l['threshold']:>9.2f} | {l['precisao']:>8.4f} | {l['recall']:>7.4f} | "
            f"{l['f1']:>6.4f} | {l['tp']:>3} | {l['fp']:>3} | {l['fn']:>3} | {l['tn']:>4}"
        )


def main() -> None:
    artefato = carregar_modelo(MODEL_PATH)
    modelo = artefato["modelo"]
    encoder = artefato["localizacao_encoder"]

    df = pd.read_csv(DATASET_PATH)
    X_test, y_test = reconstruir_split_teste(df, encoder)

    print(f"Conjunto de teste: {len(X_test)} linhas (fraude real: {int(y_test.sum())})")
    print("Modelo NÃO foi retreinado — apenas reavaliado com predict_proba().\n")

    linhas = avaliar_thresholds(modelo, X_test, y_test, THRESHOLDS)
    imprimir_tabela(linhas)

    print()
    print("Trade-off (não escolhido automaticamente):")
    print("  threshold mais baixo -> recall sobe, precisão cai (mais falso positivo)")
    print("  threshold mais alto  -> precisão sobe, recall cai (mais fraude não detectada)")
    print("Decisão do threshold final: orquestrador/usuário, conforme objetivo do negócio.")


if __name__ == "__main__":
    main()