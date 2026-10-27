import { useState, type KeyboardEvent } from "react";
import { motion } from "framer-motion";
import { Send, Sparkles } from "lucide-react";

interface Props {
  onSend: (content: string) => void;
  disabled?: boolean;
}

const suggestions = [
  "Show recent contacts",
  "Create a deal for $5,000",
  "Score my leads",
  "Summarise today's activities",
];

export function ChatInput({ onSend, disabled }: Props) {
  const [value, setValue] = useState("");

  const handleSend = () => {
    if (!value.trim() || disabled) return;
    onSend(value.trim());
    setValue("");
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="border-t border-border bg-background px-4 py-3">
      {/* Quick suggestions */}
      {!value && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="mb-2 flex flex-wrap gap-2"
        >
          {suggestions.map((s) => (
            <button
              key={s}
              onClick={() => onSend(s)}
              className="inline-flex items-center gap-1 rounded-full bg-primary/5 px-3 py-1.5 text-xs font-medium text-primary ring-1 ring-primary/10 transition hover:bg-primary/10"
            >
              <Sparkles size={12} />
              {s}
            </button>
          ))}
        </motion.div>
      )}

      {/* Input bar */}
      <div className="flex items-end gap-2">
        <textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask your AI CRM assistant…"
          rows={1}
          disabled={disabled}
          className="flex-1 resize-none rounded-xl border border-border bg-muted px-4 py-3 text-sm outline-none placeholder:text-muted-foreground focus:ring-2 focus:ring-primary/30 transition disabled:opacity-50"
        />
        <button
          onClick={handleSend}
          disabled={!value.trim() || disabled}
          className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-sm transition hover:opacity-90 disabled:opacity-40"
        >
          <Send size={18} />
        </button>
      </div>
    </div>
  );
}
