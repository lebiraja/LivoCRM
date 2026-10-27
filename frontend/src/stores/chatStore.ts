import { create } from "zustand";
import type { ChatSession, ChatMessage, WsStatus, ConfirmationPayload } from "@/types";

interface ChatState {
  /* --- Data --- */
  sessions: ChatSession[];
  activeSessionId: string | null;
  messages: ChatMessage[];
  pendingConfirmation: ConfirmationPayload | null;

  /* --- UI state --- */
  loading: boolean;
  streaming: boolean;
  wsStatus: WsStatus;

  /* --- Actions --- */
  setSessions: (sessions: ChatSession[]) => void;
  addSession: (session: ChatSession) => void;
  setActiveSessionId: (id: string | null) => void;
  setMessages: (messages: ChatMessage[]) => void;
  addMessage: (message: ChatMessage) => void;
  updateLastAiMessage: (content: string) => void;
  updateSessionTitle: (sessionId: string, title: string) => void;
  setPendingConfirmation: (confirmation: ConfirmationPayload | null) => void;
  setLoading: (loading: boolean) => void;
  setStreaming: (streaming: boolean) => void;
  setWsStatus: (status: WsStatus) => void;
  reset: () => void;
}

const initialState = {
  sessions: [] as ChatSession[],
  activeSessionId: null as string | null,
  messages: [] as ChatMessage[],
  pendingConfirmation: null as ConfirmationPayload | null,
  loading: false,
  streaming: false,
  wsStatus: "disconnected" as WsStatus,
};

export const useChatStore = create<ChatState>((set) => ({
  ...initialState,

  setSessions: (sessions) => set({ sessions }),
  addSession: (session) =>
    set((s) => ({ sessions: [session, ...s.sessions] })),
  setActiveSessionId: (id) => set({ activeSessionId: id }),

  setMessages: (messages) => set({ messages }),
  addMessage: (message) =>
    set((s) => ({ messages: [...s.messages, message] })),

  updateLastAiMessage: (content) =>
    set((s) => {
      const msgs = [...s.messages];
      for (let i = msgs.length - 1; i >= 0; i--) {
        if (msgs[i].role === "assistant") {
          msgs[i] = { ...msgs[i], content };
          break;
        }
      }
      return { messages: msgs };
    }),

  updateSessionTitle: (sessionId, title) =>
    set((s) => ({
      sessions: s.sessions.map((sess) =>
        sess.id === sessionId ? { ...sess, title } : sess
      ),
    })),

  setPendingConfirmation: (confirmation) => set({ pendingConfirmation: confirmation }),

  setLoading: (loading) => set({ loading }),
  setStreaming: (streaming) => set({ streaming }),
  setWsStatus: (status) => set({ wsStatus: status }),
  reset: () => set(initialState),
}));
