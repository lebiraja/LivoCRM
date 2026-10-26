import { useCallback, useEffect, useState, type FormEvent } from "react";
import { toast } from "sonner";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { appointmentsApi } from "@/api/appointments";
import { contactsApi } from "@/api/contacts";
import { useT, type Translate } from "@/i18n";
import type { MessageKey } from "@/i18n/en";
import type { Appointment, AppointmentStatus } from "@/lib/api-schemas";
import type { Contact } from "@/types";
import { formatINR, formatISTDateTime, istLocalToIso } from "@/lib/format";
import { notifyApiError } from "@/lib/notifyError";
import { cn } from "@/lib/utils";
import { useLocaleStore } from "@/stores/localeStore";

const statusKeys: Record<AppointmentStatus, MessageKey> = {
  booked: "appointments.status.booked",
  confirmed: "appointments.status.confirmed",
  completed: "appointments.status.completed",
  no_show: "appointments.status.no_show",
  cancelled: "appointments.status.cancelled",
  rescheduled: "appointments.status.rescheduled",
};

// Colour is never the only carrier: every status is also written out as text
const statusTones: Record<AppointmentStatus, string> = {
  booked: "text-foreground",
  confirmed: "text-foreground",
  completed: "text-success",
  no_show: "text-overdue",
  cancelled: "text-muted-foreground",
  rescheduled: "text-muted-foreground",
};

const formSchema = z.object({
  contact_id: z.string().min(1),
  starts_at: z.string().min(1),
  fee: z.string().trim().regex(/^\d+(\.\d{1,2})?$/),
  notes: z.string().max(500),
});

type FormField = keyof z.infer<typeof formSchema>;
type FieldErrors = Partial<Record<FormField, MessageKey>>;

const fieldErrorKeys: Record<FormField, MessageKey> = {
  contact_id: "appointments.error.contact",
  starts_at: "appointments.error.startsAt",
  fee: "appointments.error.fee",
  notes: "appointments.error.notes",
};

const emptyValues = { contact_id: "", starts_at: "", fee: "", notes: "" };

export function AppointmentsPage() {
  const t = useT();
  const locale = useLocaleStore((s) => s.locale);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [contacts, setContacts] = useState<Contact[]>([]);

  const refresh = useCallback(async () => {
    try {
      setAppointments(await appointmentsApi.list());
      setLoadError(false);
    } catch (error) {
      setLoadError(true);
      notifyApiError(error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const openForm = async () => {
    setFormOpen(true);
    try {
      const response = await contactsApi.list({ limit: 100 });
      setContacts(response.items);
    } catch (error) {
      notifyApiError(error);
    }
  };

  const changeStatus = async (appointment: Appointment, status: AppointmentStatus) => {
    setBusyId(appointment.id);
    try {
      const updated = await appointmentsApi.updateStatus(appointment.id, status);
      setAppointments((prev) => prev.map((item) => (item.id === updated.id ? updated : item)));
      toast.success(t("appointments.statusChanged", { status: t(statusKeys[status]) }));
    } catch (error) {
      notifyApiError(error);
    } finally {
      setBusyId(null);
    }
  };

  const handleCreated = (created: Appointment) => {
    setAppointments((prev) => [...prev, created]);
    setFormOpen(false);
    toast.success(t("appointments.booked"));
  };

  return (
    <section aria-labelledby="appointments-heading" className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <h1 id="appointments-heading" className="font-serif text-4xl leading-tight">
          {t("appointments.title")}
        </h1>
        {!formOpen && (
          <Button onClick={openForm}>{t("appointments.new")}</Button>
        )}
      </header>

      {formOpen && (
        <AppointmentForm
          contacts={contacts}
          t={t}
          onCancel={() => setFormOpen(false)}
          onCreated={handleCreated}
        />
      )}

      {loading ? (
        <div className="space-y-px" aria-hidden="true">
          {[0, 1, 2].map((item) => (
            <Skeleton key={item} className="h-24 w-full rounded-none" />
          ))}
        </div>
      ) : loadError ? (
        <div role="alert" className="flex flex-wrap items-center justify-between gap-3 border border-destructive/40 p-4">
          <p className="min-w-0 text-sm">{t("common.loadFailed")}</p>
          <Button variant="outline" onClick={() => void refresh()}>
            {t("common.retry")}
          </Button>
        </div>
      ) : appointments.length === 0 ? (
        <div className="space-y-3 border-y border-border py-10">
          <h2 className="font-serif text-2xl">{t("appointments.empty.title")}</h2>
          <p className="max-w-prose text-muted-foreground">{t("appointments.empty.body")}</p>
        </div>
      ) : (
        <ul className="border-t border-border">
          {appointments.map((appointment) => {
            const open = appointment.status === "booked" || appointment.status === "confirmed";
            return (
              <li key={appointment.id} className="grid min-w-0 gap-2 border-b border-border py-4">
                <div className="flex min-w-0 flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
                  <p className="min-w-0 break-words text-lg font-medium">{appointment.contact_name}</p>
                  <span className={cn("text-sm font-semibold", statusTones[appointment.status])}>
                    {t(statusKeys[appointment.status])}
                  </span>
                </div>
                <p className="min-w-0 break-words text-sm text-muted-foreground tabular-nums">
                  {formatISTDateTime(appointment.starts_at, locale)} · {formatINR(appointment.fee_inr)}
                </p>
                {appointment.notes && <p className="min-w-0 break-words text-sm">{appointment.notes}</p>}
                {open && (
                  <div className="flex flex-wrap gap-2">
                    <Button
                      variant="outline"
                      className="min-h-11 md:min-h-8"
                      disabled={busyId === appointment.id}
                      onClick={() => changeStatus(appointment, "completed")}
                    >
                      {t("appointments.markCompleted")}
                    </Button>
                    <Button
                      variant="outline"
                      className="min-h-11 md:min-h-8"
                      disabled={busyId === appointment.id}
                      onClick={() => changeStatus(appointment, "no_show")}
                    >
                      {t("appointments.markNoShow")}
                    </Button>
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

interface AppointmentFormProps {
  contacts: Contact[];
  t: Translate;
  onCancel: () => void;
  onCreated: (appointment: Appointment) => void;
}

function AppointmentForm({ contacts, t, onCancel, onCreated }: AppointmentFormProps) {
  const [values, setValues] = useState(emptyValues);
  const [errors, setErrors] = useState<FieldErrors>({});
  const [saving, setSaving] = useState(false);

  const setField = (field: FormField, value: string) => setValues((prev) => ({ ...prev, [field]: value }));

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const result = formSchema.safeParse(values);
    if (!result.success) {
      const next: FieldErrors = {};
      for (const issue of result.error.issues) {
        const field = issue.path[0];
        if (field === "contact_id" || field === "starts_at" || field === "fee" || field === "notes") {
          next[field] ??= fieldErrorKeys[field];
        }
      }
      setErrors(next);
      return;
    }

    setErrors({});
    setSaving(true);
    try {
      const created = await appointmentsApi.create({
        contact_id: result.data.contact_id,
        starts_at: istLocalToIso(result.data.starts_at),
        fee_inr: Number(result.data.fee),
        notes: result.data.notes.trim() || undefined,
      });
      onCreated(created);
    } catch (error) {
      notifyApiError(error);
    } finally {
      setSaving(false);
    }
  };

  const fieldClass = "h-11 w-full rounded-md border border-input bg-background px-3 text-base md:h-9 md:text-sm";

  return (
    <form noValidate onSubmit={handleSubmit} className="grid gap-4 border-y border-border py-5 md:grid-cols-2">
      <div className="grid min-w-0 gap-2">
        <Label htmlFor="appointment-contact">{t("appointments.field.contact")}</Label>
        {contacts.length === 0 ? (
          <p className="text-sm text-muted-foreground">{t("appointments.noContacts")}</p>
        ) : (
          <select
            id="appointment-contact"
            value={values.contact_id}
            aria-invalid={errors.contact_id ? true : undefined}
            aria-describedby={errors.contact_id ? "appointment-contact-error" : undefined}
            onChange={(event) => setField("contact_id", event.target.value)}
            className={fieldClass}
          >
            <option value="">—</option>
            {contacts.map((contact) => (
              <option key={contact.id} value={contact.id}>
                {contact.name}
              </option>
            ))}
          </select>
        )}
        {errors.contact_id && (
          <p id="appointment-contact-error" className="text-sm text-destructive">
            {t(errors.contact_id)}
          </p>
        )}
      </div>

      <div className="grid min-w-0 gap-2">
        <Label htmlFor="appointment-starts">{t("appointments.field.startsAt")}</Label>
        <Input
          id="appointment-starts"
          type="datetime-local"
          value={values.starts_at}
          aria-invalid={errors.starts_at ? true : undefined}
          aria-describedby={errors.starts_at ? "appointment-starts-error" : undefined}
          onChange={(event) => setField("starts_at", event.target.value)}
          className="h-11 text-base md:h-9 md:text-sm"
        />
        {errors.starts_at && (
          <p id="appointment-starts-error" className="text-sm text-destructive">
            {t(errors.starts_at)}
          </p>
        )}
      </div>

      <div className="grid min-w-0 gap-2">
        <Label htmlFor="appointment-fee">{t("appointments.field.fee")}</Label>
        <Input
          id="appointment-fee"
          type="text"
          inputMode="decimal"
          value={values.fee}
          aria-invalid={errors.fee ? true : undefined}
          aria-describedby={errors.fee ? "appointment-fee-error" : undefined}
          onChange={(event) => setField("fee", event.target.value)}
          className="h-11 text-base md:h-9 md:text-sm"
        />
        {errors.fee && (
          <p id="appointment-fee-error" className="text-sm text-destructive">
            {t(errors.fee)}
          </p>
        )}
      </div>

      <div className="grid min-w-0 gap-2 md:col-span-2">
        <Label htmlFor="appointment-notes">{t("appointments.field.notes")}</Label>
        <Textarea
          id="appointment-notes"
          rows={2}
          value={values.notes}
          aria-invalid={errors.notes ? true : undefined}
          aria-describedby={errors.notes ? "appointment-notes-error" : undefined}
          onChange={(event) => setField("notes", event.target.value)}
          className="text-base md:text-sm"
        />
        {errors.notes && (
          <p id="appointment-notes-error" className="text-sm text-destructive">
            {t(errors.notes)}
          </p>
        )}
      </div>

      <div className="flex flex-wrap gap-2 md:col-span-2">
        <Button type="submit" disabled={saving} className="min-h-11 md:min-h-8">
          {saving ? t("common.loading") : t("common.save")}
        </Button>
        <Button type="button" variant="outline" className="min-h-11 md:min-h-8" onClick={onCancel}>
          {t("common.cancel")}
        </Button>
      </div>
    </form>
  );
}
