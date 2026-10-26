const inr = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" });

const inrCompact = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  notation: "compact",
  minimumFractionDigits: 0,
  maximumFractionDigits: 1,
});

/** Format rupees with Indian digit grouping (₹1,23,456.00); `compact` gives ₹1.2L / ₹3.4Cr for tight spaces. */
export function formatINR(value: number, { compact = false }: { compact?: boolean } = {}): string {
  return (compact ? inrCompact : inr).format(value);
}
