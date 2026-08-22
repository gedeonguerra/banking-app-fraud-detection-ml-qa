# Model Card — Classificador de Fraude (Demonstração)

## 1. Visão geral

- **Tipo de modelo:** `RandomForestClassifier` (scikit-learn), `class_weight="balanced"`.
- **Propósito:** classificador de **demonstração** para fins educacionais e de QA
  dentro deste projeto (pirâmide de testes incluindo QA de ML). **Não é** um
  sistema de detecção de fraude em produção, não deve ser tratado como tal, e
  não foi validado para uso real com dados de transações reais.
- **Entrada:** valor da transação, horário (hora do dia), frequência do usuário
  (nº de transações nos últimos 30 dias) e localização.
- **Saída:** probabilidade de fraude (`predict_proba`) e/ou rótulo binário
  (0 = normal, 1 = fraude) conforme threshold escolhido.

## 2. Dados de treino

- **Origem:** dataset **sintético**, gerado por `ml-service/generate_dataset.py`
  (Faker + `random`, seed fixa = 42, determinístico).
- **Tamanho:** 5000 linhas.
- **Distribuição de classes:** 150 fraude (3,00%) / 4850 normal (97,00%) —
  desbalanceamento intencional, refletindo a realidade de detecção de fraude
  (não é 50/50).
- **Estrutura de geração:** pool fixo de 50 usuários simulados, cada um com
  perfil habitual (cidade habitual, valor médio de transação, frequência
  habitual). Transações fraudulentas são geradas a partir do próprio perfil do
  usuário, com 1 ou 2 desvios aplicados (valor muito acima do habitual,
  horário fora de 7h–22h, localização diferente da cidade habitual, ou
  frequência muito baixa/conta nova).
- **Features usadas no treino:** `valor`, `horario`, `frequencia_usuario`,
  `localizacao` (codificada via `LabelEncoder`, cardinalidade alta — ~50+
  cidades).
- **Split:** 80/20 treino/teste, estratificado pelo rótulo (mantém ~3% de
  fraude em ambos os splits). Seed fixa = 42.

## 3. Métricas (threshold = 0.5, resultado final aceito)

Avaliado sobre o conjunto de teste (1000 linhas, 30 fraude reais), execução
real no ambiente do autor (scikit-learn 1.9.0).

| Métrica   | Valor  |
|-----------|--------|
| Acurácia  | 0.9830 |
| Precisão  | 0.8824 |
| Recall    | 0.5000 |
| F1        | 0.6383 |

**Matriz de confusão** (`[[TN, FP], [FN, TP]]`):

```
[[968   2]
 [ 15  15]]
```

Acurácia isolada é enganosa neste dataset (um modelo que sempre prevê
"normal" já acertaria ~97%) — por isso todas as métricas acima são reportadas
em conjunto, não a acurácia sozinha.

**Threshold tuning** (predict_proba, mesmo split de teste):

| Threshold | Precisão | Recall | F1     | TP | FP | FN | TN  |
|-----------|----------|--------|--------|----|----|----|----|
| 0.5       | 0.8333   | 0.5000 | 0.6250 | 15 | 3  | 15 | 967 |
| 0.4       | 0.8333   | 0.5000 | 0.6250 | 15 | 3  | 15 | 967 |
| 0.3       | 0.6667   | 0.5333 | 0.5926 | 16 | 8  | 14 | 962 |
| 0.2       | 0.4444   | 0.5333 | 0.4848 | 16 | 20 | 14 | 950 |

Baixar o threshold recupera no máximo **1 fraude adicional** (TP 15→16, em
0.3) ao custo de multiplicar os falsos positivos por ~7x (3→20 entre 0.5 e
0.2). Ganho de recall é marginal (0.50→0.5333) e não muda a conclusão da
seção 4 — o gargalo é informação disponível ao modelo, não o ponto de corte.
Threshold=0.5 foi mantido como resultado final aceito.

## 4. Limitações conhecidas

- **Recall de 0.50 é uma limitação real e conhecida desta versão, não
  corrigida.** O modelo captura apenas metade das fraudes do conjunto de
  teste (15 de 30) em threshold=0.5.

- **Causa raiz investigada e confirmada** (não é hipótese — os 14 falsos
  negativos em threshold=0.2 foram identificados individualmente e
  comparados contra o perfil real do usuário de origem):
  - **8/14 (57%)** dos falsos negativos têm como único desvio de fraude a
    **localização diferente da cidade habitual do usuário**. O modelo usa
    `LabelEncoder` sobre a localização de forma isolada — não existe uma
    feature relacional que compare a localização da transação com o
    histórico do próprio usuário. O modelo não "sabe" que uma cidade é
    atípica *para aquele usuário específico*; ele só enxerga um código
    categórico solto, sem contexto de quem é o usuário.
  - **5/14 (36%)** têm como único desvio **frequência baixa**
    (`frequencia_usuario`). Esse sinal é fraco isoladamente porque a
    variação natural de frequência entre usuários normais (1–15) já se
    sobrepõe à faixa definida como "fraudulenta" no gerador (1–3) — a mesma
    conclusão foi testada como hipótese explícita e é **refutada**: 36% não
    é maioria, `localizacao_diferente` domina a contagem bruta.
  - **1/14 (7%)** teve como desvio único horário atípico; **nenhum (0/14)**
    teve valor muito acima do habitual como desvio único — esse sinal é bem
    capturado pelo modelo.

- **Threshold tuning (0.5 a 0.2) não resolve o problema de forma
  significativa.** O recall sobe apenas marginalmente (0.50→0.5333, +1
  fraude capturada) ao custo de ~7x mais falsos positivos (ver tabela da
  seção 3), confirmando que a limitação é majoritariamente de **informação
  disponível ao modelo** (falta de feature relacional usuário↔localização e
  sinal fraco de frequência isolada), não uma questão de calibração do ponto
  de decisão (threshold). Ajustar o threshold não compensa a ausência de uma
  feature que o modelo simplesmente não tem.

- **Divergência FP=2 (seção 3) vs FP=3 (tabela de threshold, linha 0.5).**
  As duas fontes usam convenções diferentes de desempate para 1 amostra cuja
  probabilidade prevista é exatamente 0.5000: `modelo.predict()` resolve esse
  empate para a classe 0 (FP=2, matriz da seção 3), enquanto o filtro
  `predict_proba >= 0.5` resolve para a classe 1 (FP=3, tabela de threshold).
  Ambos os números estão corretos para o método usado — não é bug nem
  instabilidade entre execuções. A matriz de confusão da seção 3 (via
  `predict()` nativo, FP=2) é a referência oficial deste card.

- **Caminhos de melhoria identificados, mas não implementados nesta versão**
  (ficam para decisão explícita em rodada futura, fora do escopo já
  fechado da Fase 2): feature relacional explícita (ex.: "localização atual
  é diferente da cidade habitual do usuário?" como booleano/distância, em vez
  de código categórico solto), e/ou engenharia de feature para frequência
  relativa ao histórico do próprio usuário em vez de valor absoluto.

- **Viés potencial.** O pool de apenas 50 usuários sintéticos limita a
  diversidade de padrões comportamentais representados no treino. Perfis de
  usuário reais provavelmente têm variação muito maior (ex.: mais faixas de
  valor médio, mais frequências habituais distintas, mais cidades por usuário
  ao longo do tempo) do que o gerador sintético captura com 50 perfis fixos.
  Isso **não foi testado quantitativamente** nesta versão — é uma limitação
  estrutural do dataset sintético, sinalizada, não corrigida.

- **Dataset sintético.** Todas as métricas e limitações acima refletem o
  comportamento do modelo sobre dados gerados artificialmente (Faker), não
  dados reais de transações bancárias. Resultados não são generalizáveis a
  produção sem revalidação em dados reais.