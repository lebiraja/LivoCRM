import { describe, expect, it } from "vitest";
import { aiHealthSchema } from "./api-schemas";

describe("aiHealthSchema", () => {
  it("flattens the backend pool into one row per key", () => {
    const parsed = aiHealthSchema.parse({
      provider: "groq",
      keys: 2,
      pool: [
        {
          key_id: "aaaa1111",
          models: { "openai/gpt-oss-20b": { state: "ready", remaining_tokens: 7000 } },
        },
        {
          key_id: "bbbb2222",
          models: {
            "openai/gpt-oss-20b": { state: "cooling", remaining_tokens: 0 },
            "openai/gpt-oss-120b": { state: "ready", remaining_tokens: 5000 },
          },
        },
      ],
    });
    expect(parsed.keys).toEqual([
      { key_id: "aaaa1111", state: "ready", remaining_tokens: 7000 },
      { key_id: "bbbb2222", state: "cooling", remaining_tokens: 0 },
    ]);
  });

  it("shows a key that has not been used yet as ready with unknown tokens", () => {
    const parsed = aiHealthSchema.parse({ provider: "groq", keys: 1, pool: [{ key_id: "cccc3333", models: {} }] });
    expect(parsed.keys).toEqual([{ key_id: "cccc3333", state: "ready", remaining_tokens: null }]);
  });
});
