import client from "./client";
import type { ChatSession, ChatMessage, ChatSendResponse } from "@/types";

/** Backend response shape for GET /chat/sessions/{id} */
interface ChatSessionDetail extends ChatSession {
  messages: ChatMessage[];
}

export const chatApi = {
  /** List all sessions for the current user. */
  listSessions: async (): Promise<ChatSession[]> => {
    const { data } = await client.get<ChatSession[]>("/chat/sessions");
    return data;
  },

  /** Create a new chat session. */
  createSession: async (): Promise<ChatSession> => {
    const { data } = await client.post<ChatSession>("/chat/sessions");
    return data;
  },

  /** Get messages for a session (via session detail endpoint). */
  getMessages: async (sessionId: string): Promise<ChatMessage[]> => {
    const { data } = await client.get<ChatSessionDetail>(
      `/chat/sessions/${sessionId}`
    );
    return data.messages;
  },

  /** Send a message and receive the AI response. */
  sendMessage: async (
    sessionId: string,
    message: string
  ): Promise<ChatSendResponse> => {
    const { data } = await client.post<ChatSendResponse>(
      `/chat/sessions/${sessionId}/message`,
      { message }
    );
    return data;
  },
};
