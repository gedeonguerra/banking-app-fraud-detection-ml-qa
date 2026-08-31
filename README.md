# Banking App — Fraud Detection ML QA

> Fork do [Cypress Real World App](https://github.com/cypress-io/cypress-realworld-app) com uma feature de **detecção de fraude via Machine Learning** adicionada por cima, e uma pirâmide de testes que cobre dados, modelo, API, LLM e end-to-end.

Projeto de portfólio pessoal de **Gedeon Guerra**, focado em QA Engineering com especialização em teste de sistemas de ML/IA.

---

## O que este projeto é

A base é a aplicação bancária de demonstração da Cypress (React + Express). Em cima dela foi adicionada uma feature própria: ao criar uma transação, ela passa por um classificador de fraude (scikit-learn) e, se marcada como suspeita, a aplicação exibe um alerta e o usuário pode pedir uma explicação em linguagem natural gerada por um LLM.

O objetivo não é a feature em si — é usar essa feature como pretexto para montar e documentar uma pirâmide de testes completa em cima de um sistema com ML e LLM embutidos, do jeito que um QA real precisaria testar.

## O que diferencia este fork do original

O RWA original testa uma aplicação de pagamentos comum (UI, API, componentes). Este fork adiciona uma camada que a maioria dos projetos de portfólio de QA não tem: teste de um pipeline de Machine Learning e de uma integração com LLM, com as preocupações específicas que cada um exige — qualidade de dataset, regressão de métricas de modelo, contrato de API, alucinação, prompt injection e timeout/resiliência.

## A feature: detecção de fraude

- **Modelo:** `RandomForestClassifier` (scikit-learn), treinado sobre um dataset sintético de 5.000 transações (gerado com Faker, seed fixa), com desbalanceamento intencional de ~3% de fraude — reflete a realidade de detecção de fraude, não um dataset 50/50 artificial.
- **API:** microserviço FastAPI (`ml-service/api.py`) com `GET /health` e `POST /predict-fraud`, threshold fixo em 0.5.
- **Model Card documentado** (`ml-service/model_card.md`): métricas reais do modelo (precisão 0.88, recall 0.50, F1 0.64), com a causa raiz do recall limitado investigada e registrada — 8 de 14 falsos negativos vêm da falta de uma feature relacional entre localização da transação e o histórico do próprio usuário. É tratado explicitamente como um **modelo de demonstração educacional**, não um sistema de detecção de fraude pronto para produção.
- **Explicação por LLM** (`ml-service/llm_explainer.py`): quando uma transação é marcada como suspeita, o usuário pode pedir uma explicação em linguagem natural do porquê. O LLM nunca decide se é fraude — só explica a decisão já tomada pelo modelo, usando exclusivamente os dados estruturados da transação.

## Pirâmide de testes

| Camada | O quê | Onde | Como roda |
|---|---|---|---|
| 1 — Dados | Qualidade e integridade do dataset sintético | `tests/data/test_dataset_quality.py` | `pytest` |
| 2 — Modelo | Regressão de métricas contra um baseline commitado (`baseline_metricas.json`) | `tests/model/test_model_quality.py` | `pytest` |
| 3 — API | Contrato da API de predição, in-process via `TestClient` (sem subir servidor) | `tests/api/test_predict_fraud_contract.py` | `pytest` |
| 4 — E2E | Fluxo completo na UI, com backend, frontend e ml-service reais rodando via HTTP | `cypress/tests/e2e/fraud-alert.spec.js` | Cypress |
| 5 — LLM | Prompt injection (OWASP LLM01), alucinação/fundamentação e resiliência a timeout | `tests/llm/` | `pytest` |

A Camada 5 é 100% determinística e sem custo: os testes que dependem de uma API real de LLM são marcados com `@pytest.mark.live` e pulados automaticamente sem `OPENAI_API_KEY` no ambiente — o mesmo princípio de "CI verde sem depender de conta paga" usado no resto do projeto. O teste de injection cobre tanto o isolamento do prompt (dado de usuário nunca é tratado como instrução) quanto a heurística de detecção, incluindo casos de falso positivo/negativo.

## CI/CD

Pipeline no GitHub Actions com dois jobs, o segundo dependente do primeiro (`needs:`):

1. **Camadas 1, 2, 3 e 5 (Python)** — dados, modelo, contrato de API e testes de LLM, tudo `pytest`, sem precisar subir servidor.
2. **Camada 4 (E2E)** — sobe o `ml-service` (uvicorn) e a aplicação (backend + frontend RWA) de verdade, espera os healthchecks (`wait-on`) e roda o Cypress contra o ambiente real.

## Como rodar

```bash
# instala dependências JS
yarn

# instala dependências Python
pip install -r ml-service/requirements.txt pytest httpx

# roda as camadas 1, 2, 3 e 5 (pytest)
pytest tests/data/ tests/model/ tests/api/ tests/llm/ -v

# sobe o ml-service
cd ml-service && uvicorn api:app --reload

# sobe a aplicação (outro terminal, na raiz do projeto)
yarn dev

# roda o E2E (Cypress)
yarn cypress:open
```

## Metodologia

Este projeto foi construído com apoio de ferramentas de IA como parte do fluxo de trabalho — da mesma forma que uso engenharia de prompt no meu dia a dia de QA. As decisões de arquitetura, o que testar em cada camada, a investigação da causa raiz da limitação do modelo (seção 4 do model card) e a validação de cada teste rodando de fato foram feitas e revisadas por mim.

## Autor

**Gedeon Guerra** — QA Engineer, em especialização em teste de sistemas de AI/ML.

[GitHub](https://github.com/gedeonguerra) · [LinkedIn](#)

---

**Happy Testing! 🧪**