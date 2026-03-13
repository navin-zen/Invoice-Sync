// This import needed even though we don't use React directly
// The <Provider> JSX line will be converted into a call to
// React.createComponent
import { StrictMode } from "react";
import ReactDOM from "react-dom/client";
import { Provider } from "react-redux";
import { applyMiddleware, createStore } from "redux";
import { composeWithDevTools } from "redux-devtools-extension";
import logger from "redux-logger";
import createSagaMiddleWare from "redux-saga";

import { App } from "./components";
import type { DbChooseColumnsEntrypointArg } from "./definitions";
import { INITIAL_STATE, reducer } from "./reducers";
import { helloSaga } from "./sagas";

export function DbColumnChooser(ts_arg: DbChooseColumnsEntrypointArg) {
  const sagaMiddleware = createSagaMiddleWare();
  const composeEnhancers = composeWithDevTools({});
  const store = createStore(
    reducer,
    INITIAL_STATE,
    // @ts-ignore
    composeEnhancers(applyMiddleware(sagaMiddleware, logger)),
  );
  const root = ReactDOM.createRoot(document.getElementById(ts_arg.id) as HTMLElement);
  sagaMiddleware.run(helloSaga);
  root.render(
    <StrictMode>
      {
        // @ts-ignore
        <Provider store={store}>
          <App
            dbColumns={ts_arg.dbColumns}
            mappingSpec={ts_arg.invoicingSpec}
            exampleData={ts_arg.exampleData}
            urls={ts_arg.urls}
            initialColumnMapping={ts_arg.initialColumnMapping}
            table={ts_arg.table}
          />
        </Provider>
      }
    </StrictMode>,
  );
}

// @ts-expect-error does not exist on type 'Window & typeof globalThis'
window.DbColumnChooser = DbColumnChooser;
