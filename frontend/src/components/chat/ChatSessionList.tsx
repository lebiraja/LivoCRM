import { motion } from "framer-motion";
import { Plus, MessageSquare } from "lucide-react";
import type { ChatSession } from "@/types";
import { cn } from "@/lib/utils";

interface Props {
  sessions: ChatSession[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
}

export function ChatSessionList({ sessions, activeId, onSelect, onNew }: Props) {
  return (
    <aside className="flex h-full w-64 flex-col border-r border-border bg-muted/30">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <h2 className="text-sm font-semibold text-foreground">Conversations</h2>
        <button
          onClick={onNew}
          className="flex h-7 w-7 items-center justify-center rounded-lg text-muted-foreground transition hover:bg-muted hover:text-foreground"
        >
          <Plus size={16} />
        </button>
      </div>

      {/* Session list */}
      <div className="flex-1 overflow-y-auto py-2 px-2 space-y-1">
        {sessions.length === 0 && (
          <p className="px-2 py-4 text-center text-xs text-muted-foreground">
            No conversations yet. Start a new chat!
          </p>
        )}
        {sessions.map((s) => (
          <motion.button
            key={s.id}
            whileHover={{ scale: 1.01 }}
            whileTap={{ scale: 0.99 }}
            onClick={() => onSelect(s.id)}
            className={cn(
              "flex w-full items-center gap-2 rounded-lg px-3 py-2.5 text-left text-sm transition",
              s.id === activeId
                ? "bg-primary/10 text-primary font-medium"
                : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
            )}
          >
            <MessageSquare size={14} className="shrink-0" />
            <div className="min-w-0 flex-1">
              <p className="truncate font-medium">{s.title}</p>
              <p className="truncate text-xs opacity-60">{s.preview || "—"}</p>
            </div>
          </motion.button>
        ))}
      </div>
    </aside>
  );
}
