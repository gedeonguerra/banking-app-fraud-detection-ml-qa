import { subDays } from "date-fns";
import { getTransactionsForUserByObj, transactionsWithinDateRange } from "./database";

const FRAUD_SERVICE_URL = "http://localhost:8000/predict-fraud";
const FRAUD_SERVICE_TIMEOUT_MS = 1500;

export type FraudCheckResult = {
  fraude_provavel: boolean;
  probabilidade: number;
  threshold_usado: number;
};

// Reaproveita o padrão de busca já existente em database.ts
// (getTransactionsForUserByObj + transactionsWithinDateRange), em vez de
// inventar uma query nova.
const contarTransacoesUltimos30Dias = (userId: string): number => {
  const agora = new Date();
  const inicio = subDays(agora, 30).toISOString();
  const fim = agora.toISOString();

  const transacoesDoUsuario = getTransactionsForUserByObj(userId, {});
  return transactionsWithinDateRange(inicio, fim, transacoesDoUsuario).length;
};

// Best-effort: NUNCA lança exceção. Qualquer falha (timeout, serviço fora do
// ar, HTTP não-2xx — incluindo 422 de localização desconhecida, JSON
// inválido) retorna null. Quem chama decide o que fazer com null (Fase 2.4:
// só logar).
export const checarFraude = async (
  userId: string,
  valorEmUnidadeReal: number,
  localizacao?: string
): Promise<FraudCheckResult | null> => {
  try {
    const horario = new Date().getHours();
    const frequenciaUsuario = contarTransacoesUltimos30Dias(userId);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), FRAUD_SERVICE_TIMEOUT_MS);

    const response = await fetch(FRAUD_SERVICE_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        valor: valorEmUnidadeReal,
        horario,
        frequencia_usuario: frequenciaUsuario,
        localizacao: localizacao ?? "desconhecida", // sem location -> ms-service tende a 422 (limitação já documentada); tratado abaixo como falha best-effort
      }),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      console.warn(`[fraud-check] ms-service respondeu ${response.status} para userId=${userId}`);
      return null;
    }

    return (await response.json()) as FraudCheckResult;
  } catch (err) {
    console.warn(`[fraud-check] falha ao consultar ms-service para userId=${userId}:`, err);
    return null;
  }
};