import client from "./client";
import type { Activity, ActivityCreate, PaginatedResponse } from "@/types";

export const activitiesApi = {
  /** GET /activities/?skip=&limit=&contact_id=&deal_id= → PaginatedResponse<Activity> */
  list: async (params?: {
    contact_id?: string;
    deal_id?: string;
    activity_type?: string;
    skip?: number;
    limit?: number;
  }): Promise<PaginatedResponse<Activity>> => {
    const { data } = await client.get<PaginatedResponse<Activity>>("/activities/", { params });
    return data;
  },

  /** POST /activities/ */
  create: async (payload: ActivityCreate): Promise<Activity> => {
    const { data } = await client.post<Activity>("/activities/", payload);
    return data;
  },

  /** DELETE /activities/{id} */
  delete: async (id: string): Promise<void> => {
    await client.delete(`/activities/${id}`);
  },
};
