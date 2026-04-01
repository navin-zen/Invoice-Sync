import type { SyncStatus } from "./state";

export enum ActionCode {
  INCREMENT = "increment",
  GENERIC_REQUEST = "generic-request",
  SET_SYNC_STATUS = "set-sync-status",
  SET_SYNC_ERRORS_ACTION = "set-sync-errors-action",
  SET_SYNC_MESSAGE = "set-sync-message",
}

interface IncrementAction {
  type: ActionCode.INCREMENT;
}

type RequestType = "sync-invoices";

export interface GenericRequestAction {
  type: ActionCode.GENERIC_REQUEST;
  request: RequestType;
}

export interface SyncInvoicesStatusResponse {
  completed: boolean;
  errors: string[];
  message: string;
}

export interface SetSyncStatusAction {
  type: ActionCode.SET_SYNC_STATUS;
  value: SyncStatus;
}

export interface SetSyncErrorsAction {
  type: ActionCode.SET_SYNC_ERRORS_ACTION;
  errors: Array<string>;
}

export interface SetSyncMessageAction {
  type: ActionCode.SET_SYNC_MESSAGE;
  message: string;
}

export type Action = IncrementAction | GenericRequestAction | SetSyncStatusAction | SetSyncErrorsAction | SetSyncMessageAction;

export function incrementAction(): IncrementAction {
  return {
    type: ActionCode.INCREMENT,
  };
}

export function genericRequestAction(request: RequestType): GenericRequestAction {
  return {
    type: ActionCode.GENERIC_REQUEST,
    request,
  };
}

export function setSyncStatusAction(value: SyncStatus): SetSyncStatusAction {
  return {
    type: ActionCode.SET_SYNC_STATUS,
    value,
  };
}

export function setSyncErrorsAction(errors: Array<string>): SetSyncErrorsAction {
  return {
    type: ActionCode.SET_SYNC_ERRORS_ACTION,
    errors,
  };
}

export function setSyncMessageAction(message: string): SetSyncMessageAction {
  return {
    type: ActionCode.SET_SYNC_MESSAGE,
    message,
  };
}
