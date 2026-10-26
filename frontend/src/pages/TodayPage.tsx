import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { followUpsApi } from "@/api/followUps";
import { recoveryApi } from "@/api/recovery";
import { useT, type Translate } from "@/i18n";
import type { MessageKey } from "@/i18n/en";
import type { FollowUp, FollowUpReason, RecoverySummary } from "@/lib/api-schemas";
import { formatISTDateTime } from "@/lib/format";
import { notifyApiError } from "@/lib/notifyError";
import { useLocaleStore, type Locale } from "@/stores/localeStore";

const reasonKeys: Record<FollowUpReason, MessageKey> = {
  reminder_24h: "today.reason.reminder_24h",
  reminder_2h: "today.reason.reminder_2h",
  no_show_recovery: "today.reason.no_show_recovery",
  lead_followup: "today.reason.lead_followup",
  manual: "today.reason.manual",
};

export function TodayPage() {
  const t = useT();
  const locale = useLocaleStore((s) => s.locale);
  const [tasks, setTasks] = useState<FollowUp[]>([]);
  const [loading, setLoading] = useState(true);
  const [tasksError, setTasksError] = useState(false);
  const [summary, setSummary] = useState<RecoverySummary | null>(null);
  const [summaryError, setSummaryError] = useState(false);
  const [asOf, setAsOf] = useState(0);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  const refreshTasks = useCallback(async () => {
    try {
      const list = await followUpsApi.list();
      setTasks(list);
      setAsOf(Date.now());
      setTasksError(false);
    } catch (error) {
      setTasksError(true);
      notifyApiError(error);
    } finally {
      setLoading(false);
    }
  }, []);

  const refreshSummary = useCallback(async () => {
    try {
      setSummary(await recoveryApi.summary(30));
      setSummaryError(false);
    } catch {
      setSummaryError(true);
    }
  }, []);

  useEffect(() => {
    void refreshTasks();
    void refreshSummary();
  }, [refreshTasks, refreshSummary]);

  const runRecovery = async () => {
    setRunning(true);
    try {
      const created = await recoveryApi.run();
      toast.success(t("today.runDone", { count: created }));
      await Promise.all([refreshTasks(), refreshSummary()]);
    } catch (error) {
      notifyApiError(error);
    } finally {
      setRunning(false);
    }
  };

  const withBusy = async (taskId: string, action: () => Promise<void>) => {
    setBusyId(taskId);
    try {
      await action();
    } catch (error) {
      notifyApiError(error);
    } finally {
      setBusyId(null);
    }
  };

  const draft = (task: FollowUp) =>
    withBusy(task.id, async () => {
      const updated = await followUpsApi.draft(task.id);
      setTasks((prev) => prev.map((item) => (item.id === updated.id ? updated : item)));
    });

  const approve = (task: FollowUp) =>
    withBusy(task.id, async () => {
      await followUpsApi.approve(task.id, locale);
      setTasks((prev) => prev.filter((item) => item.id !== task.id));
      toast.success(t("today.approved", { name: task.contact_name }));
      void refreshSummary();
    });

  const skip = (task: FollowUp) =>
    withBusy(task.id, async () => {
      await followUpsApi.skip(task.id);
      setTasks((prev) => prev.filter((item) => item.id !== task.id));
      toast(t("today.skipped", { name: task.contact_name }));
      void refreshSummary();
    });

  const dateLabel =
    asOf > 0
      ? new Intl.DateTimeFormat(locale === "ta" ? "ta-IN" : "en-IN", {
          weekday: "long",
          day: "numeric",
          month: "short",
          timeZone: "Asia/Kolkata",
        }).format(asOf)
      : null;

  return (
    <section aria-labelledby="today-heading" className="space-y-6">
      <header className="space-y-2">
        {dateLabel && <p className="text-sm text-muted-foreground">{dateLabel}</p>}
        <div className="flex flex-wrap items-end justify-between gap-3">
          <h1 id="today-heading" className="font-serif text-4xl leading-tight">
            {t("today.title")}
          </h1>
          <Button onClick={runRecovery} disabled={running}>
            {t("today.run")}
          </Button>
        </div>
        {summary && (
          <p className="font-serif text-xl leading-snug tabular-nums md:text-2xl">
            {t("today.kpi", {
              pending: summary.pending_tasks,
              noShows: summary.no_shows,
              rate: Math.round(summary.no_show_rate * 100),
            })}
          </p>
        )}
        {summaryError && <p className="text-sm text-muted-foreground">{t("today.kpiUnavailable")}</p>}
      </header>

      {loading ? (
        <div className="space-y-px" aria-hidden="true">
          {[0, 1, 2].map((item) => (
            <Skeleton key={item} className="h-28 w-full rounded-none" />
          ))}
        </div>
      ) : tasksError ? (
        <div role="alert" className="flex flex-wrap items-center justify-between gap-3 border border-destructive/40 p-4">
          <p className="min-w-0 text-sm">{t("common.loadFailed")}</p>
          <Button variant="outline" onClick={() => void refreshTasks()}>
            {t("common.retry")}
          </Button>
        </div>
      ) : tasks.length === 0 ? (
        <div className="space-y-3 border-y border-border py-10">
          <h2 className="font-serif text-2xl">{t("today.empty.title")}</h2>
          <p className="max-w-prose text-muted-foreground">{t("today.empty.body")}</p>
          <Button variant="outline" asChild>
            <Link to="/appointments">{t("today.empty.appointments")}</Link>
          </Button>
        </div>
      ) : (
        <ul className="border-t border-border">
          {tasks.map((task) => (
            <FollowUpRow
              key={task.id}
              task={task}
              locale={locale}
              asOf={asOf}
              busy={busyId === task.id}
              t={t}
              onDraft={draft}
              onApprove={approve}
              onSkip={skip}
            />
          ))}
        </ul>
      )}
    </section>
  );
}

interface FollowUpRowProps {
  task: FollowUp;
  locale: Locale;
  asOf: number;
  busy: boolean;
  t: Translate;
  onDraft: (task: FollowUp) => Promise<void>;
  onApprove: (task: FollowUp) => Promise<void>;
  onSkip: (task: FollowUp) => Promise<void>;
}

function FollowUpRow({ task, locale, asOf, busy, t, onDraft, onApprove, onSkip }: FollowUpRowProps) {
  const overdue = asOf > 0 && new Date(task.due_at).getTime() < asOf;
  const draftText = (locale === "ta" ? task.draft_ta : task.draft_en) ?? task.draft_en ?? task.draft_ta;

  return (
    <li className="grid min-w-0 gap-3 border-b border-border py-4">
      <div className="flex min-w-0 flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
        <p className="min-w-0 break-words text-lg font-medium">{task.contact_name}</p>
        {overdue && <span className="text-sm font-semibold text-overdue">{t("today.overdue")}</span>}
      </div>

      <p className="min-w-0 break-words text-sm text-muted-foreground">
        {t(reasonKeys[task.reason])}
        {" · "}
        {t("today.due", { when: formatISTDateTime(task.due_at, locale) })}
      </p>

      {task.contact_phone && (
        <a
          href={`tel:${task.contact_phone}`}
          className="w-fit break-all text-sm text-primary underline-offset-4 hover:underline"
        >
          {task.contact_phone}
        </a>
      )}

      {draftText ? (
        <p className="min-w-0 break-words rounded-md bg-muted px-3 py-2 text-sm leading-relaxed">{draftText}</p>
      ) : (
        <p className="text-sm text-muted-foreground">{t("today.noDraft")}</p>
      )}

      <div className="flex flex-wrap gap-2">
        <Button variant="outline" className="min-h-11 md:min-h-8" disabled={busy} onClick={() => onDraft(task)}>
          {draftText ? t("today.redraft") : t("today.draft")}
        </Button>
        <Button className="min-h-11 md:min-h-8" disabled={busy} onClick={() => onApprove(task)}>
          {t("today.approve")}
        </Button>
        <Button variant="ghost" className="min-h-11 md:min-h-8" disabled={busy} onClick={() => onSkip(task)}>
          {t("today.skip")}
        </Button>
      </div>
    </li>
  );
}
