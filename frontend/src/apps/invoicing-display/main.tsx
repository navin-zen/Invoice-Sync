// This import needed even though we don't use React directly
// The <Provider> JSX line will be converted into a call to
// React.createComponent
import { StrictMode } from "react";
import ReactDOM from "react-dom/client";

import { Invoicing } from "./components/invoicing-data";

export function DisplayInvoicing(id: string, invoicing_data: any) {
  const root = ReactDOM.createRoot(document.getElementById(id) as HTMLElement);
  root.render(
    <StrictMode>
      <Invoicing data={invoicing_data} />
    </StrictMode>,
  );
}

// @ts-expect-error does not exist on type 'Window & typeof globalThis'
window.DisplayInvoicing = DisplayInvoicing;
