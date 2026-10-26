import { motion } from "framer-motion";
import type { ChatMessage as ChatMessageType } from "@/types";
import { cn } from "@/lib/utils";

interface Props {
  message: ChatMessageType;
}

export function ChatMessage({ message }: Props) {
  const isUser = message.role === "user";

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className={cn("flex min-w-0 py-3", isUser ? "justify-end" : "flex-col items-start gap-1")}
    >
      {!isUser && (
        <span className="rounded-sm border border-border px-1.5 text-xs font-medium text-muted-foreground">AI</span>
      )}

      <div
        className={cn(
          "max-w-[85%] min-w-0 rounded-lg px-4 py-3 text-sm leading-relaxed md:max-w-[75%]",
          isUser ? "bg-muted text-foreground" : "px-0 text-foreground"
        )}
      >
        <p className="break-words whitespace-pre-wrap">{message.content}</p>
      </div>
    </motion.div>
  );
}
