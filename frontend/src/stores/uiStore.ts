import { create } from "zustand";

interface UIState {
  commandOpen: boolean;

  setCommandOpen: (open: boolean) => void;
}

export const useUIStore = create<UIState>((set) => ({
  commandOpen: false,

  setCommandOpen: (open) => set({ commandOpen: open }),
}));
