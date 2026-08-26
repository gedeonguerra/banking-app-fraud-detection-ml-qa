import React, { useEffect } from "react";
import { useMachine, useActor } from "@xstate/react";
import { User, TransactionPayload } from "../models";
import TransactionCreateStepOne from "../components/TransactionCreateStepOne";
import TransactionCreateStepTwo from "../components/TransactionCreateStepTwo";
import TransactionCreateStepThree from "../components/TransactionCreateStepThree";
import { createTransactionMachine } from "../machines/createTransactionMachine";
import { usersMachine } from "../machines/usersMachine";
import { debounce } from "lodash/fp";
import {
  BaseActionObject,
  Interpreter,
  ResolveTypegenMeta,
  ServiceMap,
  TypegenDisabled,
} from "xstate";
import { AuthMachineContext, AuthMachineEvents, AuthMachineSchema } from "../machines/authMachine";
import {
  SnackbarSchema,
  SnackbarContext,
  SnackbarEvents,
  Severities,
} from "../machines/snackbarMachine";
import { Stepper, Step, StepLabel } from "@mui/material";

export interface Props {
  authService: Interpreter<AuthMachineContext, AuthMachineSchema, AuthMachineEvents, any, any>;
  snackbarService: Interpreter<
    SnackbarContext,
    SnackbarSchema,
    SnackbarEvents,
    any,
    ResolveTypegenMeta<TypegenDisabled, SnackbarEvents, BaseActionObject, ServiceMap>
  >;
}

const TransactionCreateContainer: React.FC<Props> = ({ authService, snackbarService }) => {
  const [authState] = useActor(authService);
  const [, sendSnackbar] = useActor(snackbarService);

  const [createTransactionState, sendCreateTransaction, createTransactionService] =
    useMachine(createTransactionMachine);

  // Expose createTransactionService on window for Cypress
  // @ts-ignore
  window.createTransactionService = createTransactionService;

  const [usersState, sendUsers] = useMachine(usersMachine);

  useEffect(() => {
    sendUsers({ type: "FETCH" });
  }, [sendUsers]);

  const sender = authState?.context?.user;
  const setReceiver = (receiver: User) => {
    // @ts-ignore
    sendCreateTransaction({ type: "SET_USERS", sender, receiver });
  };
  const createTransaction = (payload: TransactionPayload) => {
    sendCreateTransaction("CREATE", payload);
  };
  const userListSearch = debounce(200, (payload: any) => sendUsers({ type: "FETCH", ...payload }));

  const showSnackbar = (payload: SnackbarContext) => sendSnackbar({ type: "SHOW", ...payload });

  // Fase 2.4/3.4: escuta o filho transactionDataMachine (invocado no nível raiz
  // de createTransactionMachine, para sobreviver à transição stepTwo -> stepThree)
  // para acessar a resposta real do POST /transactions, incluindo o resultado da
  // checagem de fraude, e exibir alerta na UI quando aplicável.
  useEffect(() => {
    const child = createTransactionService.children.get("transactionDataMachine");
    if (!child) return;

    // @ts-ignore - child é um Interpreter (máquina invocada), expõe subscribe
    const subscription = child.subscribe((state: any) => {
      if (state.history?.matches("creating") && state.matches("loading")) {
        const fraudCheck = state.event?.data?.fraudCheck;
        if (fraudCheck?.fraude_provavel) {
          showSnackbar({
            severity: Severities.warning,
            message: `Possível fraude detectada nesta transação (probabilidade: ${(fraudCheck.probabilidade * 100).toFixed(0)}%)`,
          });
        }
      }
    });

    return () => subscription.unsubscribe();
  }, [createTransactionService, showSnackbar]);

  let activeStep;
  if (createTransactionState.matches("stepTwo")) {
    activeStep = 1;
  } else if (createTransactionState.matches("stepThree")) {
    activeStep = 3;
  } else {
    activeStep = 0;
  }

  return (
    <>
      <Stepper activeStep={activeStep}>
        <Step key={"stepOne"}>
          <StepLabel>Select Contact</StepLabel>
        </Step>
        <Step key={"stepTwo"}>
          <StepLabel>Payment</StepLabel>
        </Step>
        <Step key={"stepThree"}>
          <StepLabel>Complete</StepLabel>
        </Step>
      </Stepper>
      {createTransactionState.matches("stepOne") && (
        <TransactionCreateStepOne
          setReceiver={setReceiver}
          users={usersState.context.results!}
          userListSearch={userListSearch}
        />
      )}
      {sender && createTransactionState.matches("stepTwo") && (
        <TransactionCreateStepTwo
          receiver={createTransactionState.context.receiver}
          sender={sender}
          createTransaction={createTransaction}
          showSnackbar={showSnackbar}
        />
      )}
      {createTransactionState.matches("stepThree") && (
        <TransactionCreateStepThree createTransactionService={createTransactionService} />
      )}
    </>
  );
};

export default TransactionCreateContainer;
