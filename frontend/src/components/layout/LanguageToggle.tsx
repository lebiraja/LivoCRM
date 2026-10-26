import { useT } from "@/i18n";
import { useLocaleStore, type Locale } from "@/stores/localeStore";
import { cn } from "@/lib/utils";

const segments: { locale: Locale; labelKey: "language.ta" | "language.en" }[] = [
  { locale: "ta", labelKey: "language.ta" },
  { locale: "en", labelKey: "language.en" },
];

/** Segmented தமிழ் | EN control. Each segment carries its own lang and aria-pressed. */
export function LanguageToggle() {
  const t = useT();
  const locale = useLocaleStore((s) => s.locale);
  const setLocale = useLocaleStore((s) => s.setLocale);

  return (
    <div
      role="group"
      aria-label={t("language.label")}
      className="inline-flex shrink-0 rounded-md border border-input p-0.5 text-sm"
    >
      {segments.map((segment) => {
        const pressed = locale === segment.locale;
        return (
          <button
            key={segment.locale}
            type="button"
            lang={segment.locale}
            aria-pressed={pressed}
            onClick={() => setLocale(segment.locale)}
            className={cn(
              "min-h-10 min-w-10 rounded-sm px-2.5 font-medium transition-colors md:min-h-8",
              pressed ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"
            )}
          >
            {t(segment.labelKey)}
          </button>
        );
      })}
    </div>
  );
}
