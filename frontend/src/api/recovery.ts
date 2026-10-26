import client from "./client";
import { recoveryRunSchema, recoverySummarySchema, type RecoverySummary } from "@/lib/api-schemas";

export const recoveryApi = {
  /** GET /recovery/summary?days= */
  summary: async (days: number): Promise<RecoverySummary> => {
    const { data } = await client.get<unknown>("/recovery/summary", { params: { days } });
    return recoverySummarySchema.parse(data);
  },

  /** POST /recovery/run: idempotently creates follow-up tasks; returns how many were new */
  run: async (): Promise<number> => {
    const { data } = await client.post<unknown>("/recovery/run", {});
    return recoveryRunSchema.parse(data).created;
  },
};
