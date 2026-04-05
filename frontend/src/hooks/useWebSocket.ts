import { useEffect, useRef, useCallback } from "react";
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

  const connect = useCallback(() => {
    if (!sessionId) return;

    const token = localStorage.getItem("access_token") || "";
    const url = `${WS_BASE}/chat/${sessionId}?token=${encodeURIComponent(token)}`;

    setWsStatus("connecting");
    const ws = new WebSocket(url);

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

    ws.onclose = () => {
      setWsStatus("disconnected");
      wsRef.current = null;

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
    connect();
    return () => {
      clearTimeout(timerRef.current);
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [connect]);

  return { send };
}
