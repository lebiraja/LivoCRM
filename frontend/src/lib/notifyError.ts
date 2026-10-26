import { isAxiosError } from "axios";
import { toast } from "sonner";
import { z } from "zod";
import { translate } from "@/i18n";
import { useLocaleStore } from "@/stores/localeStore";

const errorBodySchema = z.object({ detail: z.string() });

/**
 * Shows a failed API call as an error toast. The translated fallback is the title; the server's
 * `detail` is shown underneath only when it is plain text (FastAPI validation errors are lists).
 */
export function notifyApiError(error: unknown): void {
  const { locale } = useLocaleStore.getState();
  const body = isAxiosError(error) ? errorBodySchema.safeParse(error.response?.data) : null;
  toast.error(translate(locale, "toast.apiFallback"), {
    description: body?.success ? body.data.detail : undefined,
  });
}
