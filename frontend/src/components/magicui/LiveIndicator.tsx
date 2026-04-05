import { cn } from "@/lib/utils";

interface LiveIndicatorProps {
  label?: string;
  className?: string;
  color?: "green" | "indigo" | "amber";
}

const colorMap: Record<string, { ring: string; dot: string }> = {
  green:  { ring: "bg-emerald-500/20", dot: "bg-emerald-500" },
  indigo: { ring: "bg-indigo-500/20",  dot: "bg-indigo-500" },
  amber:  { ring: "bg-amber-500/20",   dot: "bg-amber-500" },
};

/**
 * Magic UI Live Indicator — pulsing concentric rings to show real-time status.
 */
export function LiveIndicator({
  label,
  className,
  color = "green",
}: LiveIndicatorProps) {
  const { ring, dot } = colorMap[color];

  return (
    <span className={cn("inline-flex items-center gap-1.5", className)}>
      <span className="relative flex h-2.5 w-2.5">
        {/* Outer pulsing ring */}
        <span
          className={cn(
            "absolute inline-flex h-full w-full animate-ping rounded-full opacity-75",
            ring.replace("/20", "")
          )}
          style={{ animationDuration: "1.8s" }}
        />
        {/* Inner solid dot */}
        <span className={cn("relative inline-flex h-2.5 w-2.5 rounded-full", dot)} />
      </span>
      {label && (
        <span className="text-xs font-medium text-muted-foreground">{label}</span>
      )}
    </span>
  );
}
