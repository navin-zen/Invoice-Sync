import { call, delay, fork, put, take } from "redux-saga/effects";

import { httpGet, httpPost } from "@/lib/fetch";

import { ActionCode, type GenericRequestAction, setSyncErrorsAction, setSyncStatusAction, setSyncMessageAction } from "./actions";
import type { SyncInvoicesEntrypointArg, SyncInvoicesResponse, SyncInvoicesStatusResponse } from "./definitions";

function* syncInvoices(syncUrl: string) {
  try {
    yield put(setSyncStatusAction("running"));
    yield put(setSyncErrorsAction([]));
    yield put(setSyncMessageAction("Connecting with DB")); // Immediate feedback
    // @ts-ignore
    const response = yield call(httpPost, syncUrl, "", "text/plain");
    const data: SyncInvoicesResponse = yield response.json();

    // Trigger the actual sync in the background so we can start polling immediately
    yield fork(function* () {
      try {
        yield call(httpPost, data.urls.sync_invoices, "", "text/plain");
      } catch (e) {
        console.error("Sync failed", e);
      }
    });

    yield delay(500);
    for (let i = 0; i < 1800; i++) {
      // try for 30 minutes
      // @ts-ignore
      const status_response = yield call(httpGet, data.urls.status + `?i=${i}`);
      const status: SyncInvoicesStatusResponse = yield status_response.json();
      if (status.message) {
        yield put(setSyncMessageAction(status.message));
      }
      if (status.completed) {
        yield put(setSyncStatusAction("complete"));
        yield put(setSyncErrorsAction(status.errors));
        break;
      }
      yield delay(1000);
    }
  } catch (err) { }
}

/**
 * Our Sagas, as per redux-saga https://redux-saga.js.org
 */
export function* mainSaga(ts_arg: SyncInvoicesEntrypointArg) {
  while (true) {
    // @ts-ignore
    const action = yield take([ActionCode.GENERIC_REQUEST]);
    if (action.type === ActionCode.GENERIC_REQUEST) {
      const request = (action as GenericRequestAction).request;
      if (request === "sync-invoices") {
        yield fork(syncInvoices, ts_arg.syncUrl);
      }
    }
  }
}
