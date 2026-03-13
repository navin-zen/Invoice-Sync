import React from "react";
import ReactDOM from "react-dom/client";

import type { Message } from "./entrypoint";
import { TriggerAlert } from "./trigger-alert";

export function TwAlert(id: string, messages: Message[]) {
  const root = ReactDOM.createRoot(document.getElementById(id) as HTMLElement);

  root.render(
    <React.StrictMode>
      <TriggerAlert messages={messages} />
    </React.StrictMode>,
  );
}

// @ts-ignore
window.TwAlert = TwAlert;
