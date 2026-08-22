#!/usr/bin/env python3
"""
investigate_fn.py

Investiga os 15 falsos negativos (y_test=1, modelo prevê 0 mesmo em
threshold=0.2) identificados em tune_threshold.py.

Método (para não inventar dado ausente — o CSV final não guarda qual usuário
nem quais desvios geraram cada linha de fraude):
  1. Reconstrói a geração do dataset usando a MESMA seed (42) e a MESMA
     sequência de chamadas de RNG do generate_dataset.py original, desta vez
     também guardando metadados (usuário de origem, perfil habitual, desvios
     aplicados) por linha.
  2. Verifica que essa reconstrução é FIEL: compara as colunas públicas
     (valor, horario, frequencia_usuario, localizacao, rotulo) linha a linha
     contra o CSV real já salvo. Só prossegue se baterem 100%.
  3. Reconstrói o split de teste (mesma seed/estratificação de
     train_model.py / tune_threshold.py) e junta com os metadados pelo índice
     de linha do CSV (ordem preservada, join direto).
  4. Roda predict_proba() no modelo já treinado, isola os 15 FN em
     threshold=0.2, e reporta desvio (ground truth do gerador) + comparação
     numérica real contra o perfil do usuário + probabilidade exata.
  5. Testa a hipótese: linhas com APENAS "freq_baixa" dominam os 15 FN.

Não retreina o modelo. Não altera o dataset nem o .pkl.

NOTA: import corrigido — generate_dataset.py vive em ml-service/ (não em
scripts/, que é a pasta de infraestrutura original do fork do RWA).
"""

import random
import sys
from pathlib import Path

import joblib
import pandas as pd
from faker import Faker
from sklearn.model_selection import train_test_split

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "ml-service"))
from generate_dataset import (  # noqa: E402
    N_LINHAS,
    N_USUARIOS,
    SEED,
    TAXA_FRAUDE,
    gerar_transacao_normal,
    montar_pool_usuarios,
)

DATASET_PATH = BASE_DIR / "tests" / "data" / "dataset_transacoes.csv"
MODEL_PATH = BASE_DIR / "ml-service" / "modelo_fraude.pkl"
THRESHOLD_FOCO = 0.2  # menor threshold já testado; recall ficou travado nele


def gerar_transacao_fraude_com_metadata(usuario_idx, usuario, fake, rng):
    """Réplica exata de gerar_transacao_fraude, mas também retorna os
    desvios aplicados (ground truth). Mesma sequência de chamadas de RNG."""
    base = gerar_transacao_normal(usuario, fake, rng)

    desvios_possiveis = ["valor_alto", "horario_atipico", "localizacao_diferente", "freq_baixa"]
    n_desvios = rng.choice([1, 1, 1, 2])
    desvios = rng.sample(desvios_possiveis, n_desvios)

    if "valor_alto" in desvios:
        base["valor"] = round(usuario["valor_medio"] * rng.uniform(3.0, 12.0), 2)
    if "horario_atipico" in desvios:
        base["horario"] = rng.choice(list(range(0, 7)) + [23])
    if "localizacao_diferente" in desvios:
        nova_cidade = fake.city()
        while nova_cidade == usuario["cidade_habitual"]:
            nova_cidade = fake.city()
        base["localizacao"] = nova_cidade
    if "freq_baixa" in desvios:
        base["frequencia_usuario"] = rng.randint(1, 3)

    base["rotulo"] = 1
    base["_usuario_idx"] = usuario_idx
    base["_desvios"] = ",".join(desvios)
    base["_valor_medio_usuario"] = round(usuario["valor_medio"], 2)
    base["_cidade_habitual_usuario"] = usuario["cidade_habitual"]
    base["_frequencia_habitual_usuario"] = usuario["frequencia_habitual"]
    return base


def reconstruir_com_metadata():
    rng = random.Random(SEED)
    fake = Faker()
    Faker.seed(SEED)

    usuarios = montar_pool_usuarios(fake, rng, N_USUARIOS)

    n_fraude = round(N_LINHAS * TAXA_FRAUDE)
    n_normal = N_LINHAS - n_fraude

    linhas = []
    for _ in range(n_normal):
        usuario = rng.choice(usuarios)
        row = gerar_transacao_normal(usuario, fake, rng)
        row["_usuario_idx"] = usuarios.index(usuario)
        row["_desvios"] = ""
        row["_valor_medio_usuario"] = round(usuario["valor_medio"], 2)
        row["_cidade_habitual_usuario"] = usuario["cidade_habitual"]
        row["_frequencia_habitual_usuario"] = usuario["frequencia_habitual"]
        linhas.append(row)

    for _ in range(n_fraude):
        usuario = rng.choice(usuarios)
        idx = usuarios.index(usuario)
        row = gerar_transacao_fraude_com_metadata(idx, usuario, fake, rng)
        linhas.append(row)

    rng.shuffle(linhas)
    return linhas


def verificar_fidelidade(linhas_meta: list[dict], csv_path: Path) -> pd.DataFrame:
    campos_publicos = ["valor", "horario", "frequencia_usuario", "localizacao", "rotulo"]
    df_reconstruido = pd.DataFrame(linhas_meta)
    df_real = pd.read_csv(csv_path)

    publicos_reconstruidos = df_reconstruido[campos_publicos].reset_index(drop=True)
    publicos_reais = df_real[campos_publicos].reset_index(drop=True)

    identico = publicos_reconstruidos.equals(publicos_reais)
    print(f"Reconstrução fiel ao CSV real (colunas públicas idênticas, linha a linha): {identico}")
    if not identico:
        raise RuntimeError(
            "Reconstrução DIVERGIU do CSV real — investigação abortada para não reportar "
            "dado inventado. Necessário revisar a réplica da sequência de RNG."
        )

    df_reconstruido = df_reconstruido.reset_index(drop=True)
    return df_reconstruido


def main():
    linhas_meta = reconstruir_com_metadata()
    df = verificar_fidelidade(linhas_meta, DATASET_PATH)

    artefato = joblib.load(MODEL_PATH)
    modelo = artefato["modelo"]
    encoder = artefato["localizacao_encoder"]

    df["localizacao_enc"] = encoder.transform(df["localizacao"])
    X = df[["valor", "horario", "frequencia_usuario", "localizacao_enc"]]
    y = df["rotulo"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=SEED
    )

    probas = modelo.predict_proba(X_test)[:, 1]
    y_pred_02 = (probas >= THRESHOLD_FOCO).astype(int)

    idx_test = X_test.index
    fn_mask = (y_test.values == 1) & (y_pred_02 == 0)
    fn_idx = idx_test[fn_mask]
    fn_probas = probas[fn_mask]

    print(f"\nTotal de falsos negativos em threshold={THRESHOLD_FOCO}: {len(fn_idx)}\n")

    linhas_relatorio = []
    for csv_idx, proba in zip(fn_idx, fn_probas):
        linha = df.loc[csv_idx]
        desvios = linha["_desvios"].split(",") if linha["_desvios"] else []

        delta_valor = linha["valor"] - linha["_valor_medio_usuario"]
        fora_horario = not (7 <= linha["horario"] <= 22)
        loc_diferente = linha["localizacao"] != linha["_cidade_habitual_usuario"]
        freq_baixa_real = linha["frequencia_usuario"] <= 3

        linhas_relatorio.append(
            {
                "csv_idx": csv_idx,
                "proba": round(float(proba), 4),
                "desvios_geracao": "+".join(desvios) if desvios else "(nenhum?!)",
                "valor": linha["valor"],
                "valor_medio_usuario": linha["_valor_medio_usuario"],
                "delta_valor_%": round(delta_valor / linha["_valor_medio_usuario"] * 100, 1),
                "horario": linha["horario"],
                "fora_7_22h": fora_horario,
                "localizacao": linha["localizacao"],
                "cidade_habitual": linha["_cidade_habitual_usuario"],
                "loc_diferente": loc_diferente,
                "frequencia_usuario": linha["frequencia_usuario"],
                "frequencia_habitual_usuario": linha["_frequencia_habitual_usuario"],
                "freq<=3": freq_baixa_real,
            }
        )

    rel = pd.DataFrame(linhas_relatorio).sort_values("proba")
    with pd.option_context("display.max_columns", None, "display.width", 200):
        print(rel.to_string(index=False))

    print("\n--- Teste da hipótese (freq_baixa isolado domina os FN) ---")
    contagem_desvios = rel["desvios_geracao"].value_counts()
    print(contagem_desvios)

    n_total = len(rel)
    n_freq_baixa_isolado = (rel["desvios_geracao"] == "freq_baixa").sum()
    print(f"\nFN com APENAS freq_baixa como desvio: {n_freq_baixa_isolado}/{n_total}")

    if n_freq_baixa_isolado / n_total >= 0.5:
        print("CONFIRMADA: maioria (>=50%) dos FN é freq_baixa isolado.")
    else:
        print("REFUTADA (ao menos parcialmente): freq_baixa isolado NÃO é maioria dos FN — "
              "outros padrões de desvio também estão escapando do modelo.")


if __name__ == "__main__":
    main()