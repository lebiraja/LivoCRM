import { useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { navItems } from "@/components/layout/navItems";
import { useT } from "@/i18n";
import { useUIStore } from "@/stores/uiStore";

export function CommandMenu() {
  const t = useT();
  const { commandOpen, setCommandOpen } = useUIStore();
  const navigate = useNavigate();

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setCommandOpen(!commandOpen);
      }
    },
    [commandOpen, setCommandOpen]
  );

  useEffect(() => {
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  const go = (path: string) => {
    navigate(path);
    setCommandOpen(false);
  };

  return (
    <CommandDialog open={commandOpen} onOpenChange={setCommandOpen}>
      <CommandInput placeholder={t("common.search")} />
      <CommandList>
        <CommandEmpty>{t("common.noResults")}</CommandEmpty>
        <CommandGroup heading={t("nav.primary")}>
          {navItems.map((item) => (
            <CommandItem key={item.to} onSelect={() => go(item.to)}>
              <item.icon className="mr-2 h-4 w-4" />
              {t(item.labelKey)}
            </CommandItem>
          ))}
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  );
}
