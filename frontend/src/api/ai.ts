import client from "./client";
import { aiHealthSchema, type AIHealth } from "@/lib/api-schemas";

export const aiApi = {
  /** GET /ai/health: per-key state and remaining tokens; no secrets */
  health: async (): Promise<AIHealth> => {
    const { data } = await client.get<unknown>("/ai/health");
    return aiHealthSchema.parse(data);
  },
};
