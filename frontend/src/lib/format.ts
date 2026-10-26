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

/** Times are stored in UTC and shown in India Standard Time (plan 10: the UI shows IST). */
const IST = "Asia/Kolkata";

/** e.g. "27 Oct, 10:00 am" for an ISO timestamp, in IST. */
export function formatISTDateTime(iso: string, locale: string): string {
  return new Intl.DateTimeFormat(locale, {
    day: "numeric",
    month: "short",
    hour: "numeric",
    minute: "2-digit",
    timeZone: IST,
  }).format(new Date(iso));
}

/** Converts a datetime-local value that the user typed in IST into an ISO timestamp for the API. */
export function istLocalToIso(value: string): string {
  return new Date(`${value}:00+05:30`).toISOString();
}
