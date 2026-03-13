import type { SyncStatus } from "./state";

export enum ActionCode {
  INCREMENT = "increment",
  GENERIC_REQUEST = "generic-request",
  SET_SYNC_STATUS = "set-sync-status",
  SET_SYNC_ERRORS_ACTION = "set-sync-errors-action",
}

interface IncrementAction {
  type: ActionCode.INCREMENT;
}

type RequestType = "sync-invoices";

export interface GenericRequestAction {
  type: ActionCode.GENERIC_REQUEST;
  request: RequestType;
}

export interface SetSyncStatusAction {
  type: ActionCode.SET_SYNC_STATUS;
  value: SyncStatus;
}

export interface SetSyncErrorsAction {
  type: ActionCode.SET_SYNC_ERRORS_ACTION;
  errors: Array<string>;
}

export type Action = IncrementAction | GenericRequestAction | SetSyncStatusAction | SetSyncErrorsAction;

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
