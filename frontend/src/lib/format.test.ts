import { describe, expect, it } from "vitest";
import { formatINR } from "./format";

describe("formatINR", () => {
  it("uses the rupee sign and lakh/crore grouping", () => {
    expect(formatINR(1234567.5)).toBe("₹12,34,567.50");
    expect(formatINR(12500000)).toBe("₹1,25,00,000.00");
  });

  it("formats zero and negative amounts", () => {
    expect(formatINR(0)).toBe("₹0.00");
    expect(formatINR(-500)).toBe("-₹500.00");
  });

  it("abbreviates to thousand, lakh and crore when compact", () => {
    expect(formatINR(999, { compact: true })).toBe("₹999");
    expect(formatINR(50000, { compact: true })).toBe("₹50K");
    expect(formatINR(150000, { compact: true })).toBe("₹1.5L");
    expect(formatINR(12500000, { compact: true })).toBe("₹1.3Cr");
  });
});
