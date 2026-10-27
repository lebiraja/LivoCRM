import { useEffect, useRef, useCallback } from "react";
import client from "@/api/client";
import { useChatStore } from "@/stores/chatStore";

const WS_BASE =
  import.meta.env.VITE_WS_URL ||
  `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}/ws`;

interface UseWebSocketOptions {
  sessionId: string | null;
  onMessage?: (data: Record<string, unknown>) => void;
}

/**
 * Manages a WebSocket connection for a chat session with automatic
 * reconnect and heartbeat.
 */
export function useWebSocket({ sessionId, onMessage }: UseWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const retriesRef = useRef(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const setWsStatus = useChatStore((s) => s.setWsStatus);

  const closedByUsRef = useRef(false);

  const connect = useCallback(async () => {
    if (!sessionId || closedByUsRef.current) return;

    setWsStatus("connecting");
    // The JWT never goes in the URL: ask for a single-use ticket on every (re)connect
    let ticket: string;
    try {
      const { data } = await client.post<{ ticket?: unknown }>("/ws/ticket", {
        channel: "chat",
        session_id: sessionId,
      });
      if (typeof data.ticket !== "string" || !data.ticket) throw new Error("bad ticket");
      ticket = data.ticket;
    } catch {
      setWsStatus("disconnected");
      return;
    }
    if (closedByUsRef.current) return;

    const ws = new WebSocket(`${WS_BASE}/chat/${sessionId}?ticket=${encodeURIComponent(ticket)}`);

    ws.onopen = () => {
      setWsStatus("connected");
      retriesRef.current = 0;
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage?.(data);
      } catch {
        // non-JSON frame — ignore
      }
    };

    ws.onerror = () => {
      /* handled in onclose */
    };

    ws.onclose = (event) => {
      setWsStatus("disconnected");
      wsRef.current = null;

      // 4001 missing ticket, 4003 wrong user/session, 4029 too many sockets: retrying cannot help
      if (closedByUsRef.current || [4001, 4003, 4029].includes(event.code)) return;
      // Exponential back-off, max 30 s, stop after 5 retries
      if (retriesRef.current < 5) {
        const delay = Math.min(1000 * 2 ** retriesRef.current, 30_000);
        retriesRef.current++;
        timerRef.current = setTimeout(connect, delay);
      }
    };

    wsRef.current = ws;
  }, [sessionId, onMessage, setWsStatus]);

  /** Send a JSON payload through the WebSocket. */
  const send = useCallback((payload: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(payload));
    }
  }, []);

  /* Connect on mount / session change; cleanup on unmount */
  useEffect(() => {
    closedByUsRef.current = false;
    void connect();
    return () => {
      closedByUsRef.current = true;
      clearTimeout(timerRef.current);
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [connect]);

  return { send };
}
