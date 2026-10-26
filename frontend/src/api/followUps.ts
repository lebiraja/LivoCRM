import client from "./client";
import {
  approveResponseSchema,
  followUpListSchema,
  followUpSchema,
  type ApproveResponse,
  type FollowUp,
} from "@/lib/api-schemas";
import type { Locale } from "@/stores/localeStore";

export const followUpsApi = {
  /** GET /follow-ups?status=pending */
  list: async (): Promise<FollowUp[]> => {
    const { data } = await client.get<unknown>("/follow-ups", { params: { status: "pending" } });
    return followUpListSchema.parse(data);
  },

  /** POST /follow-ups/{id}/draft: fills draft_en and draft_ta */
  draft: async (id: string): Promise<FollowUp> => {
    const { data } = await client.post<unknown>(`/follow-ups/${id}/draft`, {});
    return followUpSchema.parse(data);
  },

  /** POST /follow-ups/{id}/approve: marks done and logs one simulated outbound message */
  approve: async (id: string, language: Locale): Promise<ApproveResponse> => {
    const { data } = await client.post<unknown>(`/follow-ups/${id}/approve`, { language });
    return approveResponseSchema.parse(data);
  },

  /** POST /follow-ups/{id}/skip */
  skip: async (id: string): Promise<FollowUp> => {
    const { data } = await client.post<unknown>(`/follow-ups/${id}/skip`, {});
    return followUpSchema.parse(data);
  },
};
