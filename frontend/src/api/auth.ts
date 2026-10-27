import client from "./client";
import type { User } from "@/types";

interface LoginResponse {
  authenticated: boolean;
}

export interface AuthConfig {
  registration_enabled: boolean;
}

export const authApi = {
  getConfig: async (): Promise<AuthConfig> => {
    const { data } = await client.get<AuthConfig>("/auth/config");
    return data;
  },

  /** POST /auth/login — establishes an HttpOnly browser session cookie. */
  login: async (email: string, password: string): Promise<LoginResponse> => {
    const { data } = await client.post<LoginResponse>("/auth/login", {
      email,
      password,
    });
    return data;
  },

  logout: async (): Promise<void> => {
    await client.post("/auth/logout");
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
