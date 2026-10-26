import { useCallback } from "react";
import { useLocaleStore, type Locale } from "@/stores/localeStore";
import { en, type MessageKey } from "./en";
import { ta } from "./ta";

export type Vars = Record<string, string | number>;
export type Translate = (key: MessageKey, vars?: Vars) => string;

const catalogues: Record<Locale, Record<MessageKey, string>> = { en, ta };

/** Looks up a message and fills {placeholders}. Use outside React; inside components use useT(). */
export function translate(locale: Locale, key: MessageKey, vars?: Vars): string {
  const template = catalogues[locale][key];
  if (!vars) return template;
  return template.replace(/\{(\w+)\}/g, (match, name: string) => String(vars[name] ?? match));
}

export function useT(): Translate {
  const locale = useLocaleStore((s) => s.locale);
  return useCallback((key, vars) => translate(locale, key, vars), [locale]);
}
