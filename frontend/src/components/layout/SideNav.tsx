import { NavLink } from "react-router-dom";
import { LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useT } from "@/i18n";
import { useAuthStore } from "@/stores/authStore";
import { cn } from "@/lib/utils";
import { navItems } from "./navItems";

/** Desktop and tablet navigation: a quiet rail from 768 px. Active item = accent text and a 2 px rule. */
export function SideNav() {
  const t = useT();
  const logout = useAuthStore((s) => s.logout);

  return (
    <aside className="hidden md:sticky md:top-0 md:flex md:h-dvh md:w-52 md:shrink-0 md:flex-col md:border-r md:border-border">
      <div className="flex h-14 items-center gap-2 px-5">
        <span className="font-serif text-xl tracking-tight">LivoCRM</span>
        <span aria-hidden="true" className="size-2 rounded-full bg-primary" />
      </div>

      <nav aria-label={t("nav.primary")} className="flex-1 space-y-0.5 px-2 py-4">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            className={({ isActive }) =>
              cn(
                "flex min-h-10 items-center gap-3 border-l-2 px-3 text-sm font-medium transition-colors",
                isActive
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              )
            }
          >
            <item.icon className="size-[18px] shrink-0" strokeWidth={1.5} aria-hidden="true" />
            {t(item.labelKey)}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-border p-3">
        <Button variant="ghost" className="w-full justify-start text-muted-foreground" onClick={logout}>
          <LogOut aria-hidden="true" />
          {t("common.logout")}
        </Button>
      </div>
    </aside>
  );
}
