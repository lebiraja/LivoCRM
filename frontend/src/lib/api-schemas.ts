import { z } from "zod";

// Zod schemas for the Phase 3 API (docs/plan/10-phase2-contract.md). Parsed at the API boundary.
// Money arrives as a JSON string when the backend serialises Decimal, so it is coerced to a number.

export const followUpReasonSchema = z.enum([
  "reminder_24h",
  "reminder_2h",
  "no_show_recovery",
  "lead_followup",
  "manual",
]);

export const followUpSchema = z.object({
  id: z.string(),
  contact_id: z.string(),
  contact_name: z.string(),
  contact_phone: z.string().nullable(),
  appointment_id: z.string().nullable(),
  reason: followUpReasonSchema,
  due_at: z.string(),
  status: z.enum(["pending", "done", "skipped"]),
  draft_en: z.string().nullable(),
  draft_ta: z.string().nullable(),
  channel: z.string(),
});

export const followUpListSchema = z.array(followUpSchema);

export const approveResponseSchema = z.object({
  task: followUpSchema,
  message: z.object({
    id: z.string(),
    language: z.enum(["en", "ta"]),
    body: z.string(),
    status: z.string(),
  }),
});

export const appointmentStatusSchema = z.enum([
  "booked",
  "confirmed",
  "completed",
  "no_show",
  "cancelled",
  "rescheduled",
]);

export const appointmentSchema = z.object({
  id: z.string(),
  contact_id: z.string(),
  contact_name: z.string(),
  starts_at: z.string(),
  fee_inr: z.coerce.number(),
  status: appointmentStatusSchema,
  notes: z.string().nullable(),
});

export const appointmentListSchema = z.array(appointmentSchema);

export const recoverySummarySchema = z.object({
  appointments: z.number(),
  no_shows: z.number(),
  no_show_rate: z.number(),
  pending_tasks: z.number(),
  messages_sent: z.number(),
  recovered_inr: z.coerce.number(),
  recovered_count: z.number(),
});

export const recoveryRunSchema = z.object({
  created: z.number(),
});

export const aiHealthSchema = z.object({
  keys: z.array(
    z.object({
      key_id: z.string(),
      state: z.string(),
      remaining_tokens: z.number().nullable(),
    })
  ),
});

export type FollowUpReason = z.infer<typeof followUpReasonSchema>;
export type FollowUp = z.infer<typeof followUpSchema>;
export type ApproveResponse = z.infer<typeof approveResponseSchema>;
export type AppointmentStatus = z.infer<typeof appointmentStatusSchema>;
export type Appointment = z.infer<typeof appointmentSchema>;
export type RecoverySummary = z.infer<typeof recoverySummarySchema>;
export type AIHealth = z.infer<typeof aiHealthSchema>;
