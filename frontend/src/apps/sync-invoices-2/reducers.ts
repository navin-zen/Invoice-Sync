import { type Action, ActionCode } from "./actions";
import type { State } from "./state";

export const INITIAL_STATE: State = {
  value: 0,
  syncStatus: "initial",
  errors: [],
};

export function reducer(state: State = INITIAL_STATE, action: Action): State {
  if (state == undefined) {
    return INITIAL_STATE;
  }
  switch (action.type) {
    case ActionCode.INCREMENT:
      return {
        ...state,
        value: state.value + 1,
      };
    case ActionCode.SET_SYNC_STATUS:
      return {
        ...state,
        syncStatus: action.value,
      };
    case ActionCode.SET_SYNC_ERRORS_ACTION:
      return {
        ...state,
        errors: action.errors,
      };
    default:
      return state;
  }
}
