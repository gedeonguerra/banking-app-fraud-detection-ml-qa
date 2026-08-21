#!/usr/bin/env python3
"""
generate_dataset.py

Gera tests/data/dataset_transacoes.csv — dataset sintético de transações
bancárias para o classificador de fraude de demonstração (Fase 2.1).

Colunas:
    valor               float, valor da transação
    horario             int (0-23), hora do dia em que a transação ocorreu
    frequencia_usuario  int, nº de transações do usuário nos últimos 30 dias
    localizacao         str, cidade onde a transação ocorreu
    rotulo              int, 0 = normal, 1 = fraude

Desenho:
    - Pool fixo de USUARIOS (~50) com perfil habitual (cidade, valor médio,
      frequência habitual), simulando recorrência.
    - Transação normal: gerada em torno do perfil habitual do próprio usuário.
    - Transação fraudulenta: gerada com pelo menos UM desvio em relação ao
      perfil habitual do próprio usuário (valor muito acima, horário fora de
      7h-22h, localização diferente da cidade habitual, ou frequência muito
      baixa / conta nova).
    - Taxa de fraude fixada em ~3% (dentro da faixa 2-4% pedida), não
      balanceado 50/50 — intencional.
    - Determinístico via SEED fixa (random, Faker).

Nota de escopo: script gera dados sintéticos para fins de QA/teste do
classificador de demonstração deste projeto. Não representa dados reais de
transações nem modela fraude bancária real.
"""

import csv
import random
from pathlib import Path

from faker import Faker

SEED = 42
N_LINHAS = 5000
TAXA_FRAUDE = 0.03  # 3%, dentro da faixa pedida (2-4%)
N_USUARIOS = 50

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "tests" / "data" / "dataset_transacoes.csv"


def montar_pool_usuarios(fake: Faker, rng: random.Random, n: int) -> list[dict]:
    """Gera perfis habituais fixos para simular recorrência de usuários."""
    usuarios = []
    for _ in range(n):
        usuarios.append(
            {
                "cidade_habitual": fake.city(),
                "valor_medio": rng.uniform(20.0, 400.0),
                "frequencia_habitual": rng.randint(1, 15),
            }
        )
    return usuarios


def gerar_transacao_normal(usuario: dict, fake: Faker, rng: random.Random) -> dict:
    valor = rng.gauss(usuario["valor_medio"], usuario["valor_medio"] * 0.25)
    valor = max(5.0, min(500.0, valor))

    horario = rng.randint(7, 22)

    frequencia = usuario["frequencia_habitual"] + rng.randint(-1, 1)
    frequencia = max(1, min(15, frequencia))

    return {
        "valor": round(valor, 2),
        "horario": horario,
        "frequencia_usuario": frequencia,
        "localizacao": usuario["cidade_habitual"],
        "rotulo": 0,
    }


def gerar_transacao_fraude(usuario: dict, fake: Faker, rng: random.Random) -> dict:
    # Parte do perfil normal do usuário e aplica 1+ desvios deliberados.
    base = gerar_transacao_normal(usuario, fake, rng)

    desvios_possiveis = ["valor_alto", "horario_atipico", "localizacao_diferente", "freq_baixa"]
    n_desvios = rng.choice([1, 1, 1, 2])  # maioria com 1 desvio, parte com 2
    desvios = rng.sample(desvios_possiveis, n_desvios)

    if "valor_alto" in desvios:
        base["valor"] = round(usuario["valor_medio"] * rng.uniform(3.0, 12.0), 2)

    if "horario_atipico" in desvios:
        base["horario"] = rng.choice(list(range(0, 7)) + [23])

    if "localizacao_diferente" in desvios:
        nova_cidade = fake.city()
        # garante que realmente é diferente da cidade habitual
        while nova_cidade == usuario["cidade_habitual"]:
            nova_cidade = fake.city()
        base["localizacao"] = nova_cidade

    if "freq_baixa" in desvios:
        base["frequencia_usuario"] = rng.randint(1, 3)

    base["rotulo"] = 1
    return base


def gerar_dataset(n_linhas: int, taxa_fraude: float, seed: int) -> list[dict]:
    rng = random.Random(seed)
    fake = Faker()
    Faker.seed(seed)

    usuarios = montar_pool_usuarios(fake, rng, N_USUARIOS)

    n_fraude = round(n_linhas * taxa_fraude)
    n_normal = n_linhas - n_fraude

    linhas = []
    for _ in range(n_normal):
        usuario = rng.choice(usuarios)
        linhas.append(gerar_transacao_normal(usuario, fake, rng))

    for _ in range(n_fraude):
        usuario = rng.choice(usuarios)
        linhas.append(gerar_transacao_fraude(usuario, fake, rng))

    rng.shuffle(linhas)
    return linhas


def salvar_csv(linhas: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    campos = ["valor", "horario", "frequencia_usuario", "localizacao", "rotulo"]
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        writer.writerows(linhas)


def main() -> None:
    linhas = gerar_dataset(N_LINHAS, TAXA_FRAUDE, SEED)
    salvar_csv(linhas, OUTPUT_PATH)

    total = len(linhas)
    fraudes = sum(1 for l in linhas if l["rotulo"] == 1)
    proporcao = fraudes / total * 100

    print(f"Arquivo gerado em: {OUTPUT_PATH}")
    print(f"Total de linhas: {total}")
    print(f"Transações fraude: {fraudes} ({proporcao:.2f}%)")
    print(f"Transações normais: {total - fraudes} ({100 - proporcao:.2f}%)")


if __name__ == "__main__":
    main()