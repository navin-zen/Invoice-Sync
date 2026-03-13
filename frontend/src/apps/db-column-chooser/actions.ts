export enum ActionCode {
  INCREMENT = "increment",
  GENERIC_REQUEST = "generic-request",
}

interface IncrementAction {
  type: ActionCode.INCREMENT;
}

type RequestType = "save-configuration";

export interface GenericRequestAction {
  type: ActionCode.GENERIC_REQUEST;
  request: RequestType;
}
export type Action = IncrementAction | GenericRequestAction;

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
