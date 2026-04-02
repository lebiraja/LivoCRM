import { create } from "zustand";
import type { User } from "@/types";
import { authApi } from "@/api/auth";

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;

  login: (email: string, password: string) => Promise<void>;
  register: (payload: {
    email: string;
    password: string;
    full_name: string;
  }) => Promise<void>;
  fetchUser: () => Promise<void>;
  logout: () => void;
  setUser: (user: User | null) => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: !!localStorage.getItem("access_token"),
  isLoading: false,

  login: async (email, password) => {
    set({ isLoading: true });
    try {
      // FastAPI returns { access_token, token_type }
      const token = await authApi.login(email, password);
      localStorage.setItem("access_token", token.access_token);
      set({ isAuthenticated: true });
      const user = await authApi.getMe();
      set({ user, isLoading: false });
    } catch (error) {
      set({ isLoading: false });
      throw error;
    }
  },

  register: async (payload) => {
    set({ isLoading: true });
    try {
      await authApi.register(payload);
      set({ isLoading: false });
    } catch (error) {
      set({ isLoading: false });
      throw error;
    }
  },

  fetchUser: async () => {
    try {
      const user = await authApi.getMe();
      set({ user, isAuthenticated: true });
    } catch {
      set({ user: null, isAuthenticated: false });
    }
  },

  logout: () => {
    localStorage.removeItem("access_token");
    set({ user: null, isAuthenticated: false });
  },

  setUser: (user) => set({ user }),
}));
