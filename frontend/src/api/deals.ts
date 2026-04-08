import client from "./client";
import type { Deal, DealCreate, DealStage, PaginatedResponse } from "@/types";

export const dealsApi = {
  /** GET /deals/?skip=&limit=&stage=&status= → PaginatedResponse<Deal> */
  list: async (params?: {
    stage?: DealStage;
    status?: string;
    skip?: number;
    limit?: number;
  }): Promise<PaginatedResponse<Deal>> => {
    const { data } = await client.get<PaginatedResponse<Deal>>("/deals/", { params });
    return data;
  },

  /** GET /deals/{id} */
  get: async (id: string): Promise<Deal> => {
    const { data } = await client.get<Deal>(`/deals/${id}`);
    return data;
  },

  /** POST /deals/ */
  create: async (payload: DealCreate): Promise<Deal> => {
    const { data } = await client.post<Deal>("/deals/", payload);
    return data;
  },

  /** PATCH /deals/{id} */
  update: async (id: string, payload: Partial<DealCreate>): Promise<Deal> => {
    const { data } = await client.patch<Deal>(`/deals/${id}`, payload);
    return data;
  },

  /** PATCH /deals/{id}/stage  — Kanban drag-and-drop */
  moveStage: async (id: string, stage: DealStage): Promise<Deal> => {
    const { data } = await client.patch<Deal>(`/deals/${id}/stage`, { stage });
    return data;
  },

  /** DELETE /deals/{id} */
  delete: async (id: string): Promise<void> => {
    await client.delete(`/deals/${id}`);
  },
};
