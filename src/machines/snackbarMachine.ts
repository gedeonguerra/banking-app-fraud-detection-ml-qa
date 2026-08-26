import { Machine, assign } from "xstate";

export interface SnackbarSchema {
  states: {
    invisible: {};
    visible: {};
  };
}

export type SnackbarEvents = { type: "SHOW" } | { type: "HIDE" };
export enum Severities {
  success = "success",
  info = "info",
  warning = "warning",
  error = "error",
}
export interface SnackbarContext {
  severity?: Severities;
  message?: string;
}

export const snackbarMachine = Machine<SnackbarContext, SnackbarSchema, SnackbarEvents>(
  {
    id: "snackbar",
    initial: "invisible",
    context: {
      severity: undefined,
      message: undefined,
    },
    states: {
      invisible: {
        entry: "resetSnackbar",
        on: { SHOW: "visible" },
      },
      visible: {
        entry: "setSnackbar",
        on: {
          HIDE: "invisible",
          // FIX (confirmado por execução real, xstate 4.38.3): sem isto, um
          // segundo SHOW chegando enquanto já está "visible" (ex.: alerta de
          // fraude assíncrono, chegando enquanto o snackbar de sucesso ainda
          // está na tela) era descartado sem nenhuma reação -- context nunca
          // atualizava. Self-transition simples já é externa (reexecuta
          // "entry"/atualiza context) e reinicia o "after" abaixo -- testado
          // isoladamente, não precisou de { internal: false }.
          SHOW: "visible",
        },
        after: {
          // after 3 seconds, transition to invisible
          3000: "invisible",
        },
      },
    },
  },
  {
    actions: {
      setSnackbar: assign((ctx, event: any) => ({
        severity: event.severity,
        message: event.message,
      })),
      resetSnackbar: assign((ctx, event: any) => ({
        severity: undefined,
        message: undefined,
      })),
    },
  }
);
