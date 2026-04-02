import { cn } from "@/lib/utils";

interface AiTypingDotsProps {
  className?: string;
}

/**
 * Magic UI AI Typing Dots — three bouncing dots shown while the AI is thinking.
 */
export function AiTypingDots({ className }: AiTypingDotsProps) {
  return (
    <span
      className={cn("inline-flex items-center gap-1", className)}
      aria-label="AI is typing"
    >
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="h-1.5 w-1.5 rounded-full bg-indigo-400"
          style={{
            animation: "typing-bounce 1.4s ease-in-out infinite",
            animationDelay: `${i * 0.16}s`,
          }}
        />
      ))}
    </span>
  );
}
