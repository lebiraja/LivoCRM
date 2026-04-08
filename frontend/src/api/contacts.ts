import client from "./client";
import type { Contact, ContactCreate, PaginatedResponse } from "@/types";

export const contactsApi = {
  /** GET /contacts/?skip=&limit=&search= → PaginatedResponse<Contact> */
  list: async (params?: {
    search?: string;
    skip?: number;
    limit?: number;
  }): Promise<PaginatedResponse<Contact>> => {
    const { data } = await client.get<PaginatedResponse<Contact>>("/contacts/", { params });
    return data;
  },

  /** GET /contacts/{id} */
  get: async (id: string): Promise<Contact> => {
    const { data } = await client.get<Contact>(`/contacts/${id}`);
    return data;
  },

  /** POST /contacts/ */
  create: async (payload: ContactCreate): Promise<Contact> => {
    const { data } = await client.post<Contact>("/contacts/", payload);
    return data;
  },

  /** PATCH /contacts/{id} */
  update: async (id: string, payload: Partial<ContactCreate>): Promise<Contact> => {
    const { data } = await client.patch<Contact>(`/contacts/${id}`, payload);
    return data;
  },

  /** DELETE /contacts/{id} */
  delete: async (id: string): Promise<void> => {
    await client.delete(`/contacts/${id}`);
  },

  bulkDelete: async (ids: string[]): Promise<void> => {
    await Promise.all(ids.map((id) => client.delete(`/contacts/${id}`)));
  },
};
