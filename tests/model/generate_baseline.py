#!/usr/bin/env python3
"""
generate_baseline.py

Gera tests/model/baseline_metricas.json a partir da execução real do modelo
já treinado (ml-service/modelo_fraude.pkl) sobre o dataset real. Rodar
manualmente (não é parte da suíte pytest) sempre que uma nova versão do
modelo for aceita deliberadamente como novo baseline.

IMPORTANTE: rodar este script no MESMO ambiente (mesma versão do
scikit-learn) usado para gerar modelo_fraude.pkl e model_card.md — números
diferem entre versões do sklearn mesmo com seed fixa (já documentado em
model_card.md). Rodar aqui, no ambiente real do usuário, não em sandbox.
"""

import json
from pathlib import Path

import sklearn

from _common import carregar_e_avaliar

OUTPUT_PATH = Path(__file__).resolve().parent / "baseline_metricas.json"


def main():
    resultado = carregar_e_avaliar()

    baseline = {
        "acuracia": resultado["acuracia"],
        "precisao": resultado["precisao"],
        "recall": resultado["recall"],
        "f1": resultado["f1"],
        "_metadata": {
            "sklearn_version": sklearn.__version__,
            "n_teste": resultado["n_teste"],
            "matriz_confusao": resultado["matriz_confusao"],
        },
    }

    OUTPUT_PATH.write_text(json.dumps(baseline, indent=2, ensure_ascii=False) + "\n")
    print(f"Baseline salvo em: {OUTPUT_PATH}")
    print(json.dumps(baseline, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()