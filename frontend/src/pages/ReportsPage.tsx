import { useEffect, useState, type ReactNode } from "react";
import { Bar, BarChart, LabelList, ResponsiveContainer, XAxis, YAxis } from "recharts";
import { analyticsApi } from "@/api/analytics";
import { recoveryApi } from "@/api/recovery";
import { useT } from "@/i18n";
import type { RecoverySummary } from "@/lib/api-schemas";
import { formatINR } from "@/lib/format";
import { notifyApiError } from "@/lib/notifyError";
import type { AnalyticsSummary } from "@/types";

interface StageCount {
  stage: string;
  count: number;
}

/** A ruled definition list: label left, numeral right. No coloured tiles. */
function Metric({ label, value, help }: { label: string; value: string; help?: string }) {
  return (
    <div className="grid min-w-0 grid-cols-[1fr_auto] items-baseline gap-x-4 border-b border-border py-3">
      <dt className="min-w-0 break-words text-sm text-muted-foreground">
        {label}
        {help && <span className="mt-1 block text-xs leading-relaxed">{help}</span>}
      </dt>
      <dd className="font-serif text-2xl tabular-nums">{value}</dd>
    </div>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="space-y-2">
      <h2 className="font-serif text-xl">{title}</h2>
      <dl className="border-t border-border">{children}</dl>
    </section>
  );
}

export function ReportsPage() {
  const t = useT();
  const [analytics, setAnalytics] = useState<AnalyticsSummary | null>(null);
  const [stages, setStages] = useState<StageCount[]>([]);
  const [recovery, setRecovery] = useState<RecoverySummary | null>(null);
  const [recoveryError, setRecoveryError] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      // allSettled so one failing source does not blank the whole report
      const [summary, winRate, recoverySummary] = await Promise.allSettled([
        analyticsApi.getSummary(),
        analyticsApi.getWinRate(),
        recoveryApi.summary(30),
      ]);

      if (summary.status === "fulfilled") setAnalytics(summary.value);
      else notifyApiError(summary.reason);

      if (winRate.status === "fulfilled") {
        setStages(Object.entries(winRate.value.stages).map(([stage, count]) => ({ stage, count })));
      } else {
        notifyApiError(winRate.reason);
      }

      if (recoverySummary.status === "fulfilled") setRecovery(recoverySummary.value);
      else setRecoveryError(true);

      setLoading(false);
    };
    void load();
  }, []);

  return (
    <section aria-labelledby="reports-heading" className="space-y-10">
      <header className="flex flex-wrap items-end justify-between gap-2">
        <h1 id="reports-heading" className="font-serif text-4xl leading-tight">
          {t("reports.title")}
        </h1>
        <p className="text-sm text-muted-foreground">{t("reports.last30")}</p>
      </header>

      {loading ? (
        <p className="text-muted-foreground" role="status">
          {t("common.loading")}
        </p>
      ) : (
        <>
          {recoveryError || !recovery ? (
            <p role="alert" className="text-sm text-muted-foreground">
              {t("reports.unavailable")}
            </p>
          ) : (
            <Section title={t("reports.recoverySection")}>
              <Metric
                label={t("reports.recovered")}
                value={formatINR(recovery.recovered_inr)}
                help={t("reports.recoveredHelp")}
              />
              <Metric
                label={t("reports.noShowRate")}
                value={`${Math.round(recovery.no_show_rate * 100)}%`}
              />
              <Metric label={t("reports.appointments")} value={recovery.appointments.toLocaleString("en-IN")} />
              <Metric label={t("reports.noShows")} value={recovery.no_shows.toLocaleString("en-IN")} />
              <Metric label={t("reports.messagesSent")} value={recovery.messages_sent.toLocaleString("en-IN")} />
              <Metric label={t("reports.pendingTasks")} value={recovery.pending_tasks.toLocaleString("en-IN")} />
            </Section>
          )}

          {analytics && (
            <Section title={t("reports.overview")}>
              <Metric label={t("reports.contacts")} value={analytics.contacts.toLocaleString("en-IN")} />
              <Metric label={t("reports.deals")} value={analytics.deals.toLocaleString("en-IN")} />
              <Metric label={t("reports.pipelineValue")} value={formatINR(analytics.pipeline_value, { compact: true })} />
              <Metric label={t("reports.wonValue")} value={formatINR(analytics.won_value, { compact: true })} />
            </Section>
          )}

          {stages.length > 0 && (
            <section className="space-y-2">
              <h2 className="font-serif text-xl">{t("reports.byStage")}</h2>
              <div className="h-56 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={stages} layout="vertical" margin={{ top: 4, right: 32, bottom: 4, left: 0 }}>
                    <XAxis type="number" hide />
                    <YAxis
                      type="category"
                      dataKey="stage"
                      width={112}
                      tickLine={false}
                      axisLine={false}
                      tick={{ fill: "var(--muted-foreground)", fontSize: 12 }}
                    />
                    <Bar dataKey="count" fill="var(--primary)" radius={[0, 3, 3, 0]} isAnimationActive={false}>
                      <LabelList dataKey="count" position="right" fill="var(--foreground)" fontSize={12} />
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </section>
          )}
        </>
      )}
    </section>
  );
}
