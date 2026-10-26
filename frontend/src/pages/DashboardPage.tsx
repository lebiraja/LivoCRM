import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  Users,
  Handshake,
  IndianRupee,
  Activity,
  Sparkles,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell,
} from "recharts";
import { toast } from "sonner";
import { analyticsApi } from "@/api/analytics";
import { activitiesApi } from "@/api/activities";
import type {
  AnalyticsSummary,
  WinRate,
  Forecast,
  Activity as ActivityType,
  ActivityType as ActivityKind,
} from "@/types";
import { formatINR } from "@/lib/format";

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.08 },
  },
};

const item = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0, transition: { duration: 0.3 } },
};

const STAGE_COLORS = ["#6366F1", "#06B6D4", "#10B981", "#F59E0B", "#F43F5E"];

const ACTIVITY_ICONS: Record<ActivityKind, React.ReactNode> = {
  call: <Activity className="h-3.5 w-3.5" />,
  email: <Activity className="h-3.5 w-3.5" />,
  meeting: <Activity className="h-3.5 w-3.5" />,
  note: <Activity className="h-3.5 w-3.5" />,
  task: <Activity className="h-3.5 w-3.5" />,
};

function StatCard({
  title,
  value,
  icon: Icon,
  color,
  suffix = "",
}: {
  title: string;
  value: number | string;
  icon: React.ElementType;
  color: string;
  suffix?: string;
}) {
  return (
    <motion.div variants={item}>
      <Card className="group relative overflow-hidden border-border/50 bg-card transition-all hover:border-border">
        <div
          className="absolute inset-0 opacity-0 transition-opacity group-hover:opacity-100"
          style={{
            background: `radial-gradient(circle at top right, ${color}08, transparent 60%)`,
          }}
        />
        <CardContent className="relative p-5">
          <div className="flex items-start justify-between">
            <div className="space-y-3">
              <p className="text-sm font-medium text-muted-foreground">
                {title}
              </p>
              <p className="text-2xl font-bold tracking-tight font-mono">
                {typeof value === "number" ? value.toLocaleString("en-IN") : value}
                {suffix}
              </p>
            </div>
            <div
              className="flex h-10 w-10 items-center justify-center rounded-xl"
              style={{ background: `${color}15` }}
            >
              <Icon className="h-5 w-5" style={{ color }} />
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}

export default function DashboardPage() {
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [winRate, setWinRate] = useState<WinRate | null>(null);
  const [forecast, setForecast] = useState<Forecast | null>(null);
  const [activities, setActivities] = useState<ActivityType[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const [s, wr, f, a] = await Promise.all([
          analyticsApi.getSummary(),
          analyticsApi.getWinRate(),
          analyticsApi.getForecast(),
          activitiesApi.list({ limit: 5 }),
        ]);
        setSummary(s);
        setWinRate(wr);
        setForecast(f);
        setActivities(a.items.slice(0, 5));
      } catch {
        toast.error("Failed to load dashboard");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  // Derive stage breakdown from WinRate.stages
  const stageData = winRate
    ? Object.entries(winRate.stages).map(([name, value]) => ({
        stage_name: name,
        total_value: value,
      }))
    : [];

  // Derive chart series from Forecast.breakdown
  const forecastData = forecast
    ? Object.entries(forecast.breakdown).map(([month, v]) => ({
        month,
        projected: v.raw,
        weighted: v.weighted,
      }))
    : [];

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <Skeleton className="h-8 w-48" />
          <Skeleton className="mt-1 h-4 w-72" />
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-36 rounded-xl" />
          ))}
        </div>
        <div className="grid gap-4 lg:grid-cols-7">
          <Skeleton className="col-span-4 h-80 rounded-xl" />
          <Skeleton className="col-span-3 h-80 rounded-xl" />
        </div>
      </div>
    );
  }

  return (
    <motion.div
      variants={container}
      initial="hidden"
      animate="show"
      className="space-y-6"
    >
      {/* Header */}
      <motion.div variants={item}>
        <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-sm text-muted-foreground">
          Your CRM overview at a glance
        </p>
      </motion.div>

      {/* Stat Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Contacts"
          value={summary?.contacts ?? 0}
          icon={Users}
          color="#6366F1"
        />
        <StatCard
          title="Open Deals"
          value={summary?.deals ?? 0}
          icon={Handshake}
          color="#06B6D4"
        />
        <StatCard
          title="Pipeline Value"
          value={formatINR(summary?.pipeline_value ?? 0)}
          icon={IndianRupee}
          color="#10B981"
        />
        <StatCard
          title="Win Rate"
          value={winRate?.win_rate?.toFixed(1) ?? "0.0"}
          icon={Activity}
          color="#F59E0B"
          suffix="%"
        />
      </div>

      {/* Charts Row */}
      <div className="grid gap-4 lg:grid-cols-7">
        {/* Revenue Forecast */}
        <motion.div variants={item} className="lg:col-span-4">
          <Card className="border-border/50">
            <CardHeader className="pb-2">
              <CardTitle className="text-base font-semibold">
                Revenue Forecast
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={forecastData}>
                    <defs>
                      <linearGradient id="projectedGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#6366F1" stopOpacity={0.3} />
                        <stop offset="100%" stopColor="#6366F1" stopOpacity={0} />
                      </linearGradient>
                      <linearGradient id="weightedGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#06B6D4" stopOpacity={0.3} />
                        <stop offset="100%" stopColor="#06B6D4" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                    <XAxis dataKey="month" stroke="var(--muted-foreground)" fontSize={12} tickLine={false} />
                    <YAxis
                      stroke="var(--muted-foreground)"
                      fontSize={12}
                      tickLine={false}
                      tickFormatter={(v: number) => formatINR(v, { compact: true })}
                    />
                    <Tooltip
                      contentStyle={{
                        background: "var(--popover)",
                        border: "1px solid var(--border)",
                        borderRadius: "8px",
                        fontSize: "12px",
                      }}
                      labelStyle={{ color: "var(--foreground)" }}
                      formatter={(value: unknown) => [
                        formatINR(Number(value)),
                        undefined,
                      ]}
                    />
                    <Area
                      type="monotone"
                      dataKey="projected"
                      stroke="#6366F1"
                      fill="url(#projectedGrad)"
                      strokeWidth={2}
                      name="Projected"
                    />
                    <Area
                      type="monotone"
                      dataKey="weighted"
                      stroke="#06B6D4"
                      fill="url(#weightedGrad)"
                      strokeWidth={2}
                      name="Weighted"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Pipeline Breakdown */}
        <motion.div variants={item} className="lg:col-span-3">
          <Card className="border-border/50">
            <CardHeader className="pb-2">
              <CardTitle className="text-base font-semibold">
                Pipeline Breakdown
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={stageData} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" horizontal={false} />
                    <XAxis
                      type="number"
                      stroke="var(--muted-foreground)"
                      fontSize={12}
                      tickLine={false}
                      tickFormatter={(v: number) => formatINR(v, { compact: true })}
                    />
                    <YAxis
                      dataKey="stage_name"
                      type="category"
                      stroke="var(--muted-foreground)"
                      fontSize={11}
                      tickLine={false}
                      width={90}
                    />
                    <Tooltip
                      contentStyle={{
                        background: "var(--popover)",
                        border: "1px solid var(--border)",
                        borderRadius: "8px",
                        fontSize: "12px",
                      }}
                      labelStyle={{ color: "var(--foreground)" }}
                      formatter={(value: unknown) => [
                        formatINR(Number(value)),
                        "Value",
                      ]}
                    />
                    <Bar dataKey="total_value" radius={[0, 4, 4, 0]}>
                      {stageData.map((_, index) => (
                        <Cell
                          key={index}
                          fill={STAGE_COLORS[index % STAGE_COLORS.length]}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>

      {/* Recent Activity */}
      <motion.div variants={item}>
        <Card className="border-border/50">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base font-semibold">
                Recent Activity
              </CardTitle>
              <Badge variant="secondary" className="text-xs">
                <Sparkles className="mr-1 h-3 w-3" />
                AI Tracked
              </Badge>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {activities.map((activity, i) => (
                <motion.div
                  key={activity.id}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="flex items-start gap-3"
                >
                  <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-muted text-muted-foreground">
                    {ACTIVITY_ICONS[activity.activity_type]}
                  </div>
                  <div className="flex-1 space-y-0.5">
                    <p className="text-sm">{activity.description}</p>
                    <p className="text-xs text-muted-foreground">
                      Contact {activity.contact_id}
                      {activity.deal_id && ` · Deal ${activity.deal_id}`}
                      {" · "}
                      {new Date(activity.created_at).toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </p>
                  </div>
                  <Badge
                    variant="outline"
                    className="shrink-0 text-[10px] uppercase"
                  >
                    {activity.activity_type}
                  </Badge>
                </motion.div>
              ))}
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </motion.div>
  );
}
