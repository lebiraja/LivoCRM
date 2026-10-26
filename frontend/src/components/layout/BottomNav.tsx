import { useState, type KeyboardEvent } from "react";
import { NavLink } from "react-router-dom";
import { LogOut, MoreHorizontal } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useT } from "@/i18n";
import { useAuthStore } from "@/stores/authStore";
import { cn } from "@/lib/utils";
import { navItems } from "./navItems";

/** Phone navigation below 768 px: four primary destinations and a "More" disclosure. */
export function BottomNav() {
  const t = useT();
  const logout = useAuthStore((s) => s.logout);
  const [moreOpen, setMoreOpen] = useState(false);

  const primary = navItems.filter((item) => item.inBottomBar);
  const more = navItems.filter((item) => !item.inBottomBar);

  const handleKeyDown = (event: KeyboardEvent<HTMLElement>) => {
    if (event.key === "Escape") setMoreOpen(false);
  };

  return (
    <nav
      aria-label={t("nav.primary")}
      onKeyDown={handleKeyDown}
      className="fixed inset-x-0 bottom-0 z-30 border-t border-border bg-background pb-[env(safe-area-inset-bottom)] md:hidden"
    >
      {moreOpen && (
        <div id="more-menu" className="grid gap-1 border-b border-border p-2">
          {more.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={() => setMoreOpen(false)}
              className={({ isActive }) =>
                cn(
                  "flex min-h-11 items-center gap-3 rounded-md px-3 text-sm font-medium",
                  isActive ? "text-primary" : "text-foreground"
                )
              }
            >
              <item.icon className="size-[18px] shrink-0" strokeWidth={1.5} aria-hidden="true" />
              {t(item.labelKey)}
            </NavLink>
          ))}
          <Button variant="ghost" className="min-h-11 justify-start text-muted-foreground" onClick={logout}>
            <LogOut aria-hidden="true" />
            {t("common.logout")}
          </Button>
        </div>
      )}

      <ul className="grid grid-cols-5">
        {primary.map((item) => (
          <li key={item.to}>
            <NavLink
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                cn(
                  "flex min-h-14 flex-col items-center justify-center gap-0.5 border-t-2 px-1 py-2 text-center text-xs leading-tight transition-colors",
                  isActive ? "border-primary text-primary" : "border-transparent text-muted-foreground"
                )
              }
            >
              <item.icon className="size-[18px] shrink-0" strokeWidth={1.5} aria-hidden="true" />
              <span className="min-w-0 break-words">{t(item.labelKey)}</span>
            </NavLink>
          </li>
        ))}
        <li>
          <button
            type="button"
            aria-expanded={moreOpen}
            aria-controls="more-menu"
            onClick={() => setMoreOpen((open) => !open)}
            className={cn(
              "flex min-h-14 w-full flex-col items-center justify-center gap-0.5 border-t-2 px-1 py-2 text-center text-xs leading-tight transition-colors",
              moreOpen ? "border-primary text-primary" : "border-transparent text-muted-foreground"
            )}
          >
            <MoreHorizontal className="size-[18px] shrink-0" strokeWidth={1.5} aria-hidden="true" />
            <span className="min-w-0 break-words">{t("common.more")}</span>
          </button>
        </li>
      </ul>
    </nav>
  );
}
