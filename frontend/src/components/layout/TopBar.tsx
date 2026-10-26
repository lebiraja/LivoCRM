import { Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useT } from "@/i18n";
import { useUIStore } from "@/stores/uiStore";
import { LanguageToggle } from "./LanguageToggle";

export function TopBar() {
  const t = useT();
  const setCommandOpen = useUIStore((s) => s.setCommandOpen);

  return (
    <header className="sticky top-0 z-20 flex h-14 items-center gap-3 border-b border-border bg-background px-4 md:px-8">
      <span className="flex items-center gap-2 font-serif text-lg md:hidden">
        LivoCRM
        <span aria-hidden="true" className="size-2 rounded-full bg-primary" />
      </span>

      <div className="ml-auto flex items-center gap-2">
        <Button
          variant="ghost"
          size="icon"
          className="size-10 md:size-8"
          aria-label={t("common.openCommandMenu")}
          onClick={() => setCommandOpen(true)}
        >
          <Search aria-hidden="true" />
        </Button>
        <LanguageToggle />
      </div>
    </header>
  );
}
