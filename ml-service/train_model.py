#!/usr/bin/env python3
"""
train_model.py

Treina o classificador de demonstração de fraude sobre
tests/data/dataset_transacoes.csv e salva o modelo treinado em
ml-service/modelo_fraude.pkl.

Modelo: RandomForestClassifier (class_weight="balanced"), escolhido por lidar
melhor com não-linearidades e classes desbalanceadas (dataset é ~97/3) do que
uma Logistic Regression simples.

Features: valor, horario, frequencia_usuario, localizacao (LabelEncoder —
cardinalidade alta, ~50 cidades, one-hot infla dimensionalidade sem ganho
claro para um classificador de demonstração).

Split: 80/20 estratificado pelo rótulo (mantém ~3% de fraude nos dois splits).

Métricas reportadas: acurácia, precisão, recall, F1 e matriz de confusão —
acurácia sozinha é enganosa neste dataset desbalanceado (um modelo que sempre
prevê "normal" já acertaria ~97%).

Nota de escopo: classificador de demonstração para fins de QA/teste deste
projeto — não é um sistema de detecção de fraude em produção.
"""

from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

SEED = 42

BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_PATH = BASE_DIR / "tests" / "data" / "dataset_transacoes.csv"
MODEL_PATH = Path(__file__).resolve().parent / "modelo_fraude.pkl"

FEATURES = ["valor", "horario", "frequencia_usuario", "localizacao"]
TARGET = "rotulo"


def carregar_dados(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"Dataset não encontrado em {path}. Rode generate_dataset.py primeiro."
        )
    return pd.read_csv(path)


def preparar_features(df: pd.DataFrame) -> tuple[pd.DataFrame, LabelEncoder]:
    df = df.copy()
    encoder = LabelEncoder()
    df["localizacao_enc"] = encoder.fit_transform(df["localizacao"])
    return df, encoder


def treinar(df: pd.DataFrame) -> dict:
    df, encoder = preparar_features(df)

    X = df[["valor", "horario", "frequencia_usuario", "localizacao_enc"]]
    y = df[TARGET]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=SEED
    )

    modelo = RandomForestClassifier(
        n_estimators=200,
        class_weight="balanced",
        random_state=SEED,
    )
    modelo.fit(X_train, y_train)

    y_pred = modelo.predict(X_test)

    metricas = {
        "acuracia": accuracy_score(y_test, y_pred),
        "precisao": precision_score(y_test, y_pred, zero_division=0),
        "recall": recall_score(y_test, y_pred, zero_division=0),
        "f1": f1_score(y_test, y_pred, zero_division=0),
        "matriz_confusao": confusion_matrix(y_test, y_pred),
        "n_treino": len(X_train),
        "n_teste": len(X_test),
        "fraude_treino": int(y_train.sum()),
        "fraude_teste": int(y_test.sum()),
    }

    return {"modelo": modelo, "encoder": encoder, "metricas": metricas}


def salvar_modelo(modelo, encoder, path: Path) -> None:
    joblib.dump({"modelo": modelo, "localizacao_encoder": encoder, "features": FEATURES}, path)


def main() -> None:
    df = carregar_dados(DATASET_PATH)
    resultado = treinar(df)
    m = resultado["metricas"]

    salvar_modelo(resultado["modelo"], resultado["encoder"], MODEL_PATH)

    print(f"Dataset: {DATASET_PATH} ({len(df)} linhas)")
    print(f"Split treino/teste: {m['n_treino']}/{m['n_teste']} (estratificado)")
    print(f"  fraude no treino: {m['fraude_treino']} | fraude no teste: {m['fraude_teste']}")
    print()
    print(f"Acurácia : {m['acuracia']:.4f}")
    print(f"Precisão : {m['precisao']:.4f}")
    print(f"Recall   : {m['recall']:.4f}")
    print(f"F1       : {m['f1']:.4f}")
    print("Matriz de confusão ([[TN, FP], [FN, TP]]):")
    print(m["matriz_confusao"])
    print()
    print(f"Modelo salvo em: {MODEL_PATH}")


if __name__ == "__main__":
    main()