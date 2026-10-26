import { motion } from "framer-motion";

/**
 * Animated typing indicator — three shimmering dots.
 */
export function ChatTypingIndicator() {
  return (
    <div className="flex items-center gap-3 py-3 px-2">
      <span className="rounded-sm border border-border px-1.5 text-xs font-medium text-muted-foreground">AI</span>

      <div className="flex items-center gap-1.5 px-1">
        {[0, 1, 2].map((i) => (
          <motion.span
            key={i}
            className="block h-2 w-2 rounded-full bg-primary/50"
            animate={{ opacity: [0.3, 1, 0.3], scale: [0.85, 1.15, 0.85] }}
            transition={{
              duration: 1,
              repeat: Infinity,
              delay: i * 0.2,
              ease: "easeInOut",
            }}
          />
        ))}
      </div>
    </div>
  );
}
