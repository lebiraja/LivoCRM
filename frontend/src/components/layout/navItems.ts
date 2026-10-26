import { BarChart3, CalendarDays, Kanban, MessageSquare, Settings, Sun, Users, type LucideIcon } from "lucide-react";
import type { MessageKey } from "@/i18n/en";

export interface NavItem {
  to: string;
  labelKey: MessageKey;
  icon: LucideIcon;
  /** Shown in the bottom bar below 768 px; the rest live under "More" */
  inBottomBar: boolean;
}

export const navItems: readonly NavItem[] = [
  { to: "/", labelKey: "nav.today", icon: Sun, inBottomBar: true },
  { to: "/appointments", labelKey: "nav.appointments", icon: CalendarDays, inBottomBar: true },
  { to: "/contacts", labelKey: "nav.contacts", icon: Users, inBottomBar: true },
  { to: "/chat", labelKey: "nav.assistant", icon: MessageSquare, inBottomBar: true },
  { to: "/pipeline", labelKey: "nav.pipeline", icon: Kanban, inBottomBar: false },
  { to: "/reports", labelKey: "nav.reports", icon: BarChart3, inBottomBar: false },
  { to: "/settings", labelKey: "nav.settings", icon: Settings, inBottomBar: false },
];
