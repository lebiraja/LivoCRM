import { create } from "zustand";
import { persist } from "zustand/middleware";

export type Locale = "en" | "ta";

interface LocaleState {
  locale: Locale;
  setLocale: (locale: Locale) => void;
}

export const useLocaleStore = create<LocaleState>()(
  persist(
    (set) => ({
      locale: "en",
      setLocale: (locale) => set({ locale }),
    }),
    { name: "livocrm-locale" }
  )
);

// Keep <html lang> in step so :lang(ta) typography and screen readers follow the toggle
document.documentElement.lang = useLocaleStore.getState().locale;
useLocaleStore.subscribe((state) => {
  document.documentElement.lang = state.locale;
});
