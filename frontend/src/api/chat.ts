import client from "./client";
import type { ChatSession, ChatMessage } from "@/types";

export const chatApi = {
  /** List all sessions for the current user. */
  listSessions: async (): Promise<ChatSession[]> => {
    const { data } = await client.get<ChatSession[]>("/chat/sessions");
    return data;
  },

  /** Create a new chat session. */
  createSession: async (title?: string): Promise<ChatSession> => {
    const { data } = await client.post<ChatSession>("/chat/sessions", {
      title: title || "New Chat",
    });
    return data;
  },

  /** Get messages for a session. */
  getMessages: async (sessionId: string): Promise<ChatMessage[]> => {
    const { data } = await client.get<ChatMessage[]>(
      `/chat/sessions/${sessionId}/messages`
    );
    return data;
  },

  /** Send a message (non-streaming fallback). */
  sendMessage: async (
    sessionId: string,
    content: string
  ): Promise<ChatMessage> => {
    const { data } = await client.post<ChatMessage>(
      `/chat/sessions/${sessionId}/messages`,
      { content }
    );
    return data;
  },

  /** Confirm an AI-proposed action. */
  confirmAction: async (confirmationId: string): Promise<void> => {
    await client.post(`/chat/confirmations/${confirmationId}/confirm`);
  },

  /** Dismiss an AI-proposed action. */
  dismissAction: async (confirmationId: string): Promise<void> => {
    await client.post(`/chat/confirmations/${confirmationId}/dismiss`);
  },
};
