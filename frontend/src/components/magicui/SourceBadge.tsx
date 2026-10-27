import { Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

interface SourceBadgeProps {
  label?: string;
  className?: string;
  variant?: "indigo" | "emerald" | "amber";
}

const variantStyles: Record<string, string> = {
  indigo: "bg-indigo-50 text-indigo-700 border-indigo-200",
  emerald: "bg-emerald-50 text-emerald-700 border-emerald-200",
  amber: "bg-amber-50 text-amber-700 border-amber-200",
};

/**
 * Magic UI Source Badge — shows "AI Captured / AI Scored" with Sparkles icon.
 */
export function SourceBadge({
  label = "AI Captured",
  className,
  variant = "indigo",
}: SourceBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-medium",
        variantStyles[variant],
        className
      )}
    >
      <Sparkles className="h-2.5 w-2.5" />
      {label}
    </span>
  );
}
