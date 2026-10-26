import { z } from "zod";
import client from "./client";

const wsTicketSchema = z.object({
  ticket: z.string().min(1),
  expires_in: z.number().int().positive(),
});

export type WsTicket = z.infer<typeof wsTicketSchema>;

export type WsTicketRequest =
  | { channel: "dashboard" }
  | { channel: "chat"; session_id: string };

export const wsApi = {
  /** POST /ws/ticket — single-use, short-lived ticket for opening a WebSocket. */
  getTicket: async (payload: WsTicketRequest): Promise<WsTicket> => {
    const { data } = await client.post<unknown>("/ws/ticket", payload);
    return wsTicketSchema.parse(data);
  },
};
