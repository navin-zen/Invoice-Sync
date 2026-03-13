import { z } from "zod";

export const Message = z.object({
  id: z.string(),
  message: z.string(),
  tag: z.enum(["debug", "info", "success", "warning", "danger"]),
  delay: z.number().nullish(),
});

export type Message = z.infer<typeof Message>;
