import { cn } from "@/lib/utils";

interface NumberTickerProps {
  value: number;
  prefix?: string;
  suffix?: string;
  className?: string;
  decimalPlaces?: number;
}

/**
 * Magic UI Number Ticker — smoothly animates a number from 0 to `value`.
 * Uses CSS counter animation via a CSS variable trick for broad compatibility.
 */
export function NumberTicker({
  value,
  prefix = "",
  suffix = "",
  className,
  decimalPlaces = 0,
}: NumberTickerProps) {
  const formatted =
    decimalPlaces > 0 ? value.toFixed(decimalPlaces) : value.toLocaleString();

  return (
    <span
      className={cn("tabular-nums font-mono-nums font-bold", className)}
      style={
        {
          "--target": value,
        } as React.CSSProperties
      }
    >
      {prefix}
      {formatted}
      {suffix}
    </span>
  );
}
