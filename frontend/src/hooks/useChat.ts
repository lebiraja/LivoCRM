import { useCallback, useEffect, useRef } from "react";
import { useChatStore } from "@/stores/chatStore";
import { chatApi } from "@/api/chat";
import { useWebSocket } from "./useWebSocket";
import type { ChatMessage } from "@/types";

/**
 * Orchestration hook – ties together the chat store, REST API,
 * and WebSocket transport.
 */
export function useChat() {
  const {
    sessions,
    activeSessionId,
    messages,
    loading,
    streaming,
    wsStatus,
    setSessions,
    addSession,
    setActiveSessionId,
    setMessages,
    addMessage,
    updateLastAiMessage,
    setLoading,
    setStreaming,
  } = useChatStore();

  const bottomRef = useRef<HTMLDivElement>(null);

  // Scroll to new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  /* ---- WebSocket message handler ---- */
  const handleWsMessage = useCallback(
    (data: Record<string, unknown>) => {
      const type = data.type as string;

      if (type === "ai_chunk") {
        updateLastAiMessage((data.content as string) ?? "");
      } else if (type === "ai_message") {
        setStreaming(false);
        const msg = data.message as ChatMessage;
        addMessage(msg);
      } else if (type === "ai_stream_start") {
        setStreaming(true);
        // Create an empty placeholder AI message
        addMessage({
          id: `temp-${Date.now()}`,
          session_id: activeSessionId || "",
          role: "assistant",
          content: "",
          created_at: new Date().toISOString(),
        });
      }
    },
    [activeSessionId, addMessage, updateLastAiMessage, setStreaming]
  );

  const { send } = useWebSocket({
    sessionId: activeSessionId,
    onMessage: handleWsMessage,
  });

  /* ---- Public actions ---- */

  /** Load all sessions. */
  const loadSessions = useCallback(async () => {
    setLoading(true);
    try {
      const data = await chatApi.listSessions();
      setSessions(data);
    } catch {
      // Fallback — create a demo session
      setSessions([]);
    } finally {
      setLoading(false);
    }
  }, [setSessions, setLoading]);

  /** Select a session and load its messages. */
  const selectSession = useCallback(
    async (id: string) => {
      setActiveSessionId(id);
      setLoading(true);
      try {
        const msgs = await chatApi.getMessages(id);
        setMessages(msgs);
      } catch {
        setMessages([]);
      } finally {
        setLoading(false);
      }
    },
    [setActiveSessionId, setMessages, setLoading]
  );

  /** Start a new chat session. */
  const newSession = useCallback(async () => {
    try {
      const session = await chatApi.createSession();
      addSession(session);
      setActiveSessionId(session.id);
      setMessages([]);
    } catch {
      // Generate local session when backend is offline
      const localSession = {
        id: `local-${Date.now()}`,
        title: "New Chat",
        status: "active",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        message_count: 0,
      };
      addSession(localSession);
      setActiveSessionId(localSession.id);
      setMessages([]);
    }
  }, [addSession, setActiveSessionId, setMessages]);

  /** Send a user message. */
  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim()) return;

      const userMsg: ChatMessage = {
        id: `user-${Date.now()}`,
        session_id: activeSessionId || "",
        role: "user",
        content: content.trim(),
        created_at: new Date().toISOString(),
      };
      addMessage(userMsg);

      // Try WebSocket first, fall back to REST
      if (wsStatus === "connected") {
        send({ type: "message", content: content.trim() });
      } else {
        setStreaming(true);
        try {
          const response = await chatApi.sendMessage(
            activeSessionId || "",
            content.trim()
          );
          // Backend returns both messages; replace the optimistic user msg
          // and add the AI response
          addMessage(response.ai_message);
        } catch {
          addMessage({
            id: `err-${Date.now()}`,
            session_id: activeSessionId || "",
            role: "assistant",
            content:
              "Sorry, I couldn't process your message. Please try again.",
            created_at: new Date().toISOString(),
          });
        } finally {
          setStreaming(false);
        }
      }
    },
    [activeSessionId, wsStatus, send, addMessage, setStreaming]
  );

  return {
    /* state */
    sessions,
    activeSessionId,
    messages,
    loading,
    streaming,
    wsStatus,
    bottomRef,

    /* actions */
    loadSessions,
    selectSession,
    newSession,
    sendMessage,
  };
}
