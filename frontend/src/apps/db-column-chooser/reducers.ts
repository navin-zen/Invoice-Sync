import { type Action, ActionCode } from "./actions";
import type { State } from "./state";

export const INITIAL_STATE: State = {
  value: 0,
};

export function reducer(state: State = INITIAL_STATE, action: Action): State {
  if (state == undefined) {
    return INITIAL_STATE;
  }
  switch (action.type) {
    case ActionCode.INCREMENT:
      return {
        value: state.value + 1,
      };
    default:
      return state;
  }
}
