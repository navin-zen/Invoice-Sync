export type SyncStatus = "initial" | "running" | "complete";

export interface State {
  value: number;
  syncStatus: SyncStatus;
  errors: Array<string>;
}
