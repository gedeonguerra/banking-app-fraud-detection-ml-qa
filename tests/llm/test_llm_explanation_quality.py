"""
test_llm_explanation_quality.py

Três frentes de teste para a explicação em linguagem natural gerada pelo
llm_explainer.py:

  1. Contrato/schema do resultado (determinístico, FakeLLMClient).
  2. Detecção de alucinação por checagem de fundamentação (determinístico).
  3. Performance/resiliência: timeout nunca trava o chamador (determinístico,
     usa um cliente falso "lento" — não depende de rede instável para ser
     confiável em CI).

Os testes marcados com @pytest.mark.live fazem uma chamada real a um LLM e
são pulados automaticamente se OPENAI_API_KEY não estiver no ambiente — o
mesmo princípio já usado no resto do projeto: CI verde sem depender de conta
paga.

Rodar (sem custo, sem API key):
    pytest tests/llm/test_llm_explanation_quality.py -v

Rodar incluindo os testes contra um provedor real:
    export OPENAI_API_KEY=sk-...
    pytest tests/llm/test_llm_explanation_quality.py -v -m live
"""

import os
import sys
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR / "ml-service"))

from llm_explainer import (  # noqa: E402
    FakeLLMClient,
    OpenAIClient,
    contains_ungrounded_claims,
    explicar_transacao,
)

TRANSACAO = {
    "valor": 150.0,
    "horario": 14,
    "frequencia_usuario": 8,
    "localizacao": "Daviston",
}
PREDICAO = {"fraude_provavel": True, "probabilidade": 0.87}

TIMEOUT_TESTE_S = 1.0


# ---------------------------------------------------------------------------
# 1. Contrato / schema
# ---------------------------------------------------------------------------

def test_resultado_tem_estrutura_esperada():
    client = FakeLLMClient(resposta="Transação sinalizada por padrão de valor e horário atípicos para o usuário.")
    resultado = explicar_transacao(TRANSACAO, PREDICAO, client, timeout_s=TIMEOUT_TESTE_S)

    assert isinstance(resultado.explicacao, str) and resultado.explicacao
    assert isinstance(resultado.gerado_em_ms, float)
    assert resultado.gerado_em_ms >= 0
    assert resultado.fallback is False


# ---------------------------------------------------------------------------
# 2. Detecção de alucinação (grounding check)
# ---------------------------------------------------------------------------

def test_detecta_alucinacao_de_localizacao():
    explicacao_alucinada = "A transação em Springfield foi sinalizada por valor incomum."
    problemas = contains_ungrounded_claims(explicacao_alucinada, TRANSACAO)

    assert any("Springfield" in p for p in problemas), (
        f"Esperava detectar menção a cidade não presente na transação real ('Daviston'); "
        f"problemas encontrados: {problemas}"
    )


def test_detecta_alucinacao_de_valor():
    explicacao_alucinada = "A transação de R$ 999,90 foi sinalizada como suspeita."
    problemas = contains_ungrounded_claims(explicacao_alucinada, TRANSACAO)

    assert any("999,90" in p for p in problemas), (
        f"Esperava detectar valor divergente do real (R$ 150.0); problemas encontrados: {problemas}"
    )


def test_nao_marca_falso_positivo_quando_explicacao_usa_so_dados_reais():
    explicacao_correta = (
        "A transação em Daviston, no valor de R$ 150,00, foi sinalizada por "
        "destoar do padrão habitual de horário deste usuário."
    )
    problemas = contains_ungrounded_claims(explicacao_correta, TRANSACAO)

    assert problemas == [], f"Não deveria haver alerta de alucinação aqui, mas encontrou: {problemas}"


# ---------------------------------------------------------------------------
# 3. Performance / resiliência — timeout nunca trava o chamador
# ---------------------------------------------------------------------------

def test_client_lento_aciona_fallback_sem_estourar_o_timeout():
    client_lento = FakeLLMClient(resposta="resposta que nunca deveria chegar", latencia_s=TIMEOUT_TESTE_S * 5)

    resultado = explicar_transacao(TRANSACAO, PREDICAO, client_lento, timeout_s=TIMEOUT_TESTE_S)

    assert resultado.fallback is True
    # Margem de 500ms sobre o timeout configurado — tolerância de agendamento
    # de thread, não sinal de que o timeout foi ignorado.
    assert resultado.gerado_em_ms <= (TIMEOUT_TESTE_S * 1000) + 500, (
        f"Chamada demorou {resultado.gerado_em_ms:.0f}ms, deveria ter sido interrompida perto de "
        f"{TIMEOUT_TESTE_S * 1000:.0f}ms pelo timeout"
    )


def test_client_que_lanca_excecao_tambem_aciona_fallback():
    class ClientQuebrado:
        def generate(self, system, user):
            raise ConnectionError("simulando provedor fora do ar")

    resultado = explicar_transacao(TRANSACAO, PREDICAO, ClientQuebrado(), timeout_s=TIMEOUT_TESTE_S)

    assert resultado.fallback is True
    assert resultado.explicacao  # fallback textual, nunca string vazia


# ---------------------------------------------------------------------------
# Testes "live" — chamada real, pulados sem OPENAI_API_KEY
# ---------------------------------------------------------------------------

@pytest.mark.live
@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="requer OPENAI_API_KEY no ambiente")
def test_chamada_real_respeita_orcamento_de_performance():
    client = OpenAIClient(timeout_s=5.0)
    resultado = explicar_transacao(TRANSACAO, PREDICAO, client, timeout_s=5.0)

    assert resultado.fallback is False
    assert resultado.gerado_em_ms < 5000


@pytest.mark.live
@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="requer OPENAI_API_KEY no ambiente")
def test_chamada_real_nao_alucina_dados_da_transacao():
    client = OpenAIClient(timeout_s=5.0)
    resultado = explicar_transacao(TRANSACAO, PREDICAO, client, timeout_s=5.0)

    problemas = contains_ungrounded_claims(resultado.explicacao, TRANSACAO)
    assert problemas == [], f"Modelo real alucinou dado(s) não presentes na transação: {problemas}"
