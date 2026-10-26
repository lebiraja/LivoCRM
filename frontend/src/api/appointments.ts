import client from "./client";
import {
  appointmentListSchema,
  appointmentSchema,
  type Appointment,
  type AppointmentStatus,
} from "@/lib/api-schemas";

export interface AppointmentCreate {
  contact_id: string;
  starts_at: string;
  fee_inr: number;
  notes?: string;
}

export const appointmentsApi = {
  /** GET /appointments */
  list: async (): Promise<Appointment[]> => {
    const { data } = await client.get<unknown>("/appointments");
    return appointmentListSchema.parse(data);
  },

  /** POST /appointments */
  create: async (payload: AppointmentCreate): Promise<Appointment> => {
    const { data } = await client.post<unknown>("/appointments", payload);
    return appointmentSchema.parse(data);
  },

  /** PATCH /appointments/{id} with a status change */
  updateStatus: async (id: string, status: AppointmentStatus): Promise<Appointment> => {
    const { data } = await client.patch<unknown>(`/appointments/${id}`, { status });
    return appointmentSchema.parse(data);
  },
};
