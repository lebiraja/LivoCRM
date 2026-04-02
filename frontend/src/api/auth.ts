import client from "./client";
import type { AuthToken, User } from "@/types";

export const authApi = {
  /** POST /auth/login  — JSON body { email, password } → { access_token, token_type } */
  login: async (email: string, password: string): Promise<AuthToken> => {
    const { data } = await client.post<AuthToken>("/auth/login", {
      email,
      password,
    });
    return data;
  },

  /** POST /auth/register */
  register: async (payload: {
    email: string;
    password: string;
    full_name: string;
  }): Promise<User> => {
    const { data } = await client.post<User>("/auth/register", payload);
    return data;
  },

  /** GET /auth/me */
  getMe: async (): Promise<User> => {
    const { data } = await client.get<User>("/auth/me");
    return data;
  },
};
