import { Search, Command } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { useAuthStore } from "@/stores/authStore";
import { useUIStore } from "@/stores/uiStore";

export function TopBar() {
  const user = useAuthStore((s) => s.user);
  const setCommandOpen = useUIStore((s) => s.setCommandOpen);

  const initials = user
    ? (user.full_name
        .split(" ")
        .map((n) => n[0])
        .join("") || "U")
      .toUpperCase()
      .slice(0, 2)
    : "U";

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between gap-4 border-b border-border bg-background/80 px-6 backdrop-blur-md">
      {/* Search */}
      <div className="relative w-full max-w-md">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Search contacts, deals, activities…"
          className="h-9 bg-muted/50 pl-9 pr-12 text-sm focus-visible:ring-1 focus-visible:ring-primary"
          onClick={() => setCommandOpen(true)}
          readOnly
        />
        <kbd className="pointer-events-none absolute right-3 top-1/2 flex h-5 -translate-y-1/2 items-center gap-0.5 rounded border border-border bg-muted px-1.5 text-[10px] font-mono text-muted-foreground">
          <Command className="h-3 w-3" />K
        </kbd>
      </div>

      {/* User */}
      <div className="flex items-center gap-3">
        <div className="text-right">
          <p className="text-sm font-medium leading-none">
            {user?.full_name}
          </p>
          <p className="text-xs text-muted-foreground">{user?.email}</p>
        </div>
        <Avatar className="h-9 w-9 border border-border">
          <AvatarFallback className="bg-primary/10 text-xs font-semibold text-primary">
            {initials}
          </AvatarFallback>
        </Avatar>
      </div>
    </header>
  );
}
