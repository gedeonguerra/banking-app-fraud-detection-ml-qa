import { omit } from "lodash/fp";
import { Machine, assign } from "xstate";
import { dataMachine } from "./dataMachine";
import { httpClient } from "../utils/asyncUtils";
import { User, TransactionCreatePayload } from "../models";
import { authService } from "./authMachine";
import { backendPort } from "../utils/portUtils";

export interface CreateTransactionMachineSchema {
  states: {
    stepOne: {};
    stepTwo: {};
    stepThree: {};
  };
}

const transactionDataMachine = dataMachine("transactionData").withConfig({
  services: {
    createData: async (ctx, event: any) => {
      const payload = omit("type", event);
      const resp = await httpClient.post(`http://localhost:${backendPort}/transactions`, payload);
      authService.send("REFRESH");
      return resp.data;
    },
    // FIX (investigação real, xstate 4.38.3): sem isto, o child fica preso em
    // "loading" para sempre (dataMachine.ts genérico invoca "fetchData" ao
    // entrar em loading, mas essa instância nunca configurava esse serviço).
    // Não importava enquanto o child morria logo após "creating" (bug antigo:
    // invoke dentro de stepTwo, parado na mesma tick da transição CREATE ->
    // stepThree). Agora que o invoke vive no nível raiz da máquina (sobrevive
    // entre stepTwo/stepThree, ver abaixo), um child preso em "loading" passa
    // a IGNORAR o CREATE da transação seguinte (loading não trata CREATE;
    // só "idle" e "success" tratam). Stub no-op leva loading -> success, que
    // já trata CREATE -> creating no dataMachine.ts genérico (padrão
    // reaproveitado, não um novo).
    fetchData: async () => ({ results: [], pageData: {} }),
  },
});

export type CreateTransactionMachineEvents =
  | { type: "SET_USERS" }
  | { type: "CREATE" }
  | { type: "RESET" };

export interface CreateTransactionMachineContext {
  sender: User;
  receiver: User;
  transactionDetails: TransactionCreatePayload;
}

export const createTransactionMachine = Machine<
  CreateTransactionMachineContext,
  CreateTransactionMachineSchema,
  CreateTransactionMachineEvents
>(
  {
    id: "createTransaction",
    initial: "stepOne",
    // FIX: invoke movido para o nível raiz (antes vivia dentro de "stepTwo").
    // Motivo confirmado por execução real: com o invoke em stepTwo, o child é
    // parado (Stopped) na MESMA tick síncrona do evento CREATE que também
    // transiciona stepTwo -> stepThree — antes da Promise HTTP real (POST
    // /transactions) resolver. A promise ainda resolve no JS puro, mas xstate
    // descarta a transição onDone num child já parado; nenhum subscriber
    // recebe o fraudCheck. No nível raiz, o invoke só seria parado se a
    // própria máquina raiz parasse — não em transições internas entre
    // stepTwo/stepThree.
    invoke: {
      id: "transactionDataMachine",
      src: transactionDataMachine,
      autoForward: true,
    },
    states: {
      stepOne: {
        entry: "clearContext",
        on: {
          SET_USERS: "stepTwo",
        },
      },
      stepTwo: {
        entry: "setSenderAndReceiver",
        on: {
          CREATE: "stepThree",
        },
      },
      stepThree: {
        entry: "setTransactionDetails",
        on: {
          RESET: "stepOne",
        },
      },
    },
  },
  {
    actions: {
      setSenderAndReceiver: assign((ctx, event: any) => ({
        sender: event.sender,
        receiver: event.receiver,
      })),
      setTransactionDetails: assign((ctx, event: any) => ({
        transactionDetails: event,
      })),
      clearContext: assign((ctx, event: any) => ({})),
    },
  }
);
