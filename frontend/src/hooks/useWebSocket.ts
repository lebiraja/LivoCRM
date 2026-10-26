import { useEffect, useRef } from "react";
import { wsApi, type WsTicketRequest } from "@/api/ws";
import type { WsStatus } from "@/types";

const WS_BASE =
  import.meta.env.VITE_WS_URL ||
  `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}/ws`;

const MAX_RETRIES = 5;
const BASE_DELAY_MS = 1000;
const MAX_DELAY_MS = 30_000;

interface UseWebSocketOptions {
  channel: "chat" | "dashboard";
  /** Session id for "chat", user id for "dashboard"; null means stay disconnected. */
  id: string | null;
  onMessage?: (data: Record<string, unknown>) => void;
  onStatus?: (status: WsStatus) => void;
}

/**
 * Opens an authenticated WebSocket using a single-use ticket from
 * POST /ws/ticket (the JWT never goes in the URL). Every connect and
 * reconnect fetches a fresh ticket; reconnects use capped exponential
 * back-off and stop once the hook unmounts or the id changes.
 */
export function useWebSocket({ channel, id, onMessage, onStatus }: UseWebSocketOptions) {
  // Latest callbacks in a ref so new handler identities don't reconnect
  const handlersRef = useRef({ onMessage, onStatus });
  useEffect(() => {
    handlersRef.current = { onMessage, onStatus };
  }, [onMessage, onStatus]);

  useEffect(() => {
    if (!id) return;

    const ticketRequest: WsTicketRequest =
      channel === "chat" ? { channel, session_id: id } : { channel };
    const url = `${WS_BASE}/${channel}/${id}`;
    let closedByUs = false;
    let ws: WebSocket | null = null;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let retries = 0;

    function scheduleReconnect() {
      handlersRef.current.onStatus?.("disconnected");
      if (retries >= MAX_RETRIES) return;
      const delay = Math.min(BASE_DELAY_MS * 2 ** retries, MAX_DELAY_MS);
      retries++;
      timer = setTimeout(connect, delay);
    }

    async function connect() {
      handlersRef.current.onStatus?.("connecting");
      let ticket: string;
      try {
        ({ ticket } = await wsApi.getTicket(ticketRequest));
      } catch {
        if (!closedByUs) scheduleReconnect();
        return;
      }
      if (closedByUs) return;

      ws = new WebSocket(`${url}?ticket=${encodeURIComponent(ticket)}`);

      ws.onopen = () => {
        retries = 0;
        handlersRef.current.onStatus?.("connected");
      };

      ws.onmessage = (event) => {
        try {
          handlersRef.current.onMessage?.(JSON.parse(event.data));
        } catch {
          // non-JSON frame (e.g. "pong") — ignore
        }
      };

      ws.onclose = () => {
        ws = null;
        if (!closedByUs) scheduleReconnect();
      };
    }

    connect();
    return () => {
      closedByUs = true;
      clearTimeout(timer);
      ws?.close();
      handlersRef.current.onStatus?.("disconnected");
    };
  }, [channel, id]);
}
