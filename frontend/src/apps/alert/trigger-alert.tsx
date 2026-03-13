import React from "react";
import { toast } from "sonner";

import { Toaster } from "@/components/ui/sonner";

import type { Message } from "./entrypoint";

interface AlertProps extends React.HTMLAttributes<HTMLDivElement> {
  messages: Message[];
}

export function TriggerMessages(messages: Message[]) {
  messages.map((message: Message) => {
    let bgColor: string;
    let icon: React.ReactElement;
    let borderColor: string;
    if (message.tag === "success") {
      icon = <i className="ph-fill ph-check-circle mr-3! h-4 w-4" />;
      borderColor = "var(--alert-success-border)";
      bgColor = "var(--alert-success-bg)";
    } else if (message.tag === "info") {
      icon = <i className="ph-fill ph-info mr-3! h-4 w-4" />;
      borderColor = "var(--alert-info-border)";
      bgColor = "var(--alert-info-bg)";
    } else if (message.tag === "warning") {
      icon = <i className="ph-fill ph-warning-circle mr-3! h-4 w-4" />;
      borderColor = "var(--alert-warning-border)";
      bgColor = "var(--alert-warning-bg)";
    } else if (message.tag === "debug") {
      icon = <i className="ph-fill ph-warning mr-3! h-4 w-4" />;
      borderColor = "var(--alert-destructive-border)";
      bgColor = "var(--alert-destructive-bg)";
    } else {
      icon = <i className="ph-fill ph-warning mr-3! h-4 w-4" />;
      borderColor = "var(--alert-destructive-border)";
      bgColor = "var(--alert-destructive-bg)";
    }
    if (!message.message.includes("cz_common_webinar_banner")) {
      console.info("User recieved message:", message.message);
      toast.custom(
        (t) => (
          <React.Fragment>
            <span style={{ color: borderColor }}>{icon}</span>
            <div className="text-md">
              <div dangerouslySetInnerHTML={{ __html: message.message }} />
            </div>
            <button type="button" className="absolute top-1 right-1" onClick={() => toast.dismiss(t)}>
              <svg
                role="img"
                aria-label="Close"
                xmlns="http://www.w3.org/2000/svg"
                width="16"
                height="16"
                fill="#000000"
                viewBox="0 0 256 256"
                data-darkreader-inline-fill=""
              >
                <path d="M128,24A104,104,0,1,0,232,128,104.11,104.11,0,0,0,128,24Zm37.66,130.34a8,8,0,0,1-11.32,11.32L128,139.31l-26.34,26.35a8,8,0,0,1-11.32-11.32L116.69,128,90.34,101.66a8,8,0,0,1,11.32-11.32L128,116.69l26.34-26.35a8,8,0,0,1,11.32,11.32L139.31,128Z" />
              </svg>
            </button>
          </React.Fragment>
        ),
        {
          id: message.id,
          className: "flex flex-row items-center min-h-16 px-6 py-2 rounded-lg min-w-96 max-w-[90vw]",
          duration: message.delay
            ? message.delay
            : message.tag === "debug" || message.tag === "danger" || message.tag === "warning"
              ? 21600000
              : 7000,
          style: {
            backgroundColor: bgColor,
            border: "none",
            color: "black",
          },
          closeButton: true,
        },
      );
    }
  });
}
export function TriggerAlert({ messages }: AlertProps) {
  // Trigger when load
  window.onload = () => {
    TriggerMessages(messages);
  };
  return <Toaster closeButton={true} position="top-left" duration={4000} />;
}
