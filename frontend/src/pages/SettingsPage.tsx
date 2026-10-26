import { useEffect, useState, type ReactNode } from "react";
import { Label } from "@/components/ui/label";
import { LanguageToggle } from "@/components/layout/LanguageToggle";
import { aiApi } from "@/api/ai";
import { useT } from "@/i18n";
import type { AIHealth } from "@/lib/api-schemas";
import { notifyApiError } from "@/lib/notifyError";
import { useAuthStore } from "@/stores/authStore";
import { useThemeStore, type Theme } from "@/stores/themeStore";

const themes: Theme[] = ["system", "light", "dark"];

function Section({ id, title, children }: { id: string; title: string; children: ReactNode }) {
  return (
    <section aria-labelledby={id} className="space-y-3 border-t border-border py-6">
      <h2 id={id} className="font-serif text-xl">
        {title}
      </h2>
      {children}
    </section>
  );
}

export function SettingsPage() {
  const t = useT();
  const user = useAuthStore((s) => s.user);
  const theme = useThemeStore((s) => s.theme);
  const setTheme = useThemeStore((s) => s.setTheme);
  const [health, setHealth] = useState<AIHealth | null>(null);
  const [healthError, setHealthError] = useState(false);

  useEffect(() => {
    const load = async () => {
      try {
        setHealth(await aiApi.health());
      } catch (error) {
        setHealthError(true);
        notifyApiError(error);
      }
    };
    void load();
  }, []);

  const handleThemeChange = (value: string) => {
    const next = themes.find((item) => item === value);
    if (next) setTheme(next);
  };

  return (
    <div className="mx-auto w-full max-w-[680px] space-y-2">
      <h1 className="font-serif text-4xl leading-tight">{t("settings.title")}</h1>

      <Section id="settings-profile" title={t("settings.profile")}>
        <dl className="grid min-w-0 gap-2 text-sm">
          <div className="grid grid-cols-[6rem_1fr] gap-3">
            <dt className="text-muted-foreground">{t("settings.name")}</dt>
            <dd className="min-w-0 break-words">{user?.full_name}</dd>
          </div>
          <div className="grid grid-cols-[6rem_1fr] gap-3">
            <dt className="text-muted-foreground">{t("settings.email")}</dt>
            <dd className="min-w-0 break-all">{user?.email}</dd>
          </div>
        </dl>
        <p className="text-sm text-muted-foreground">{t("settings.timezone")}</p>
      </Section>

      <Section id="settings-language" title={t("settings.language")}>
        <LanguageToggle />
      </Section>

      <Section id="settings-appearance" title={t("settings.appearance")}>
        <div className="grid max-w-xs gap-2">
          <Label htmlFor="settings-theme">{t("settings.appearance")}</Label>
          <select
            id="settings-theme"
            value={theme}
            onChange={(event) => handleThemeChange(event.target.value)}
            className="h-11 w-full rounded-md border border-input bg-background px-3 text-base md:h-9 md:text-sm"
          >
            <option value="system">{t("settings.theme.system")}</option>
            <option value="light">{t("settings.theme.light")}</option>
            <option value="dark">{t("settings.theme.dark")}</option>
          </select>
        </div>
      </Section>

      <Section id="settings-ai" title={t("settings.aiHealth")}>
        <p className="text-sm text-muted-foreground">{t("settings.aiHealthHelp")}</p>
        {healthError ? (
          <p role="alert" className="text-sm text-muted-foreground">
            {t("settings.aiHealthUnavailable")}
          </p>
        ) : health && health.keys.length === 0 ? (
          <p className="text-sm text-muted-foreground">{t("settings.aiHealthEmpty")}</p>
        ) : health ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-muted-foreground">
                  <th scope="col" className="py-2 pr-3 font-medium">
                    {t("settings.key")}
                  </th>
                  <th scope="col" className="py-2 pr-3 font-medium">
                    {t("settings.state")}
                  </th>
                  <th scope="col" className="py-2 text-right font-medium">
                    {t("settings.remainingTokens")}
                  </th>
                </tr>
              </thead>
              <tbody>
                {health.keys.map((key) => (
                  <tr key={key.key_id} className="border-b border-border">
                    <td className="py-3 pr-3 font-mono break-all">{key.key_id}</td>
                    <td className="py-3 pr-3 break-words">{key.state}</td>
                    <td className="py-3 text-right tabular-nums">
                      {key.remaining_tokens === null ? "—" : key.remaining_tokens.toLocaleString("en-IN")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </Section>
    </div>
  );
}
