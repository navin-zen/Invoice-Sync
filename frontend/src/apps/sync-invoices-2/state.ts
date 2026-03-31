export type SyncStatus = "initial" | "running" | "complete";

export interface State {
  value: number;
  syncStatus: SyncStatus;
  errors: Array<string>;
  syncMessage: string;
}

export const initialState: State = {
  value: 0,
  syncStatus: "initial",
  errors: [],
  syncMessage: "",
};
