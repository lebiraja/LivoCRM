import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  Users,
  Handshake,
  DollarSign,
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
import { analyticsApi } from "@/api/analytics";
import { activitiesApi } from "@/api/activities";
import type {
  AnalyticsSummary,
  WinRate,
  Forecast,
  Activity as ActivityType,
  ActivityType as ActivityKind,
} from "@/types";

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
  prefix = "",
  suffix = "",
}: {
  title: string;
  value: number | string;
  icon: React.ElementType;
  color: string;
  prefix?: string;
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
                {prefix}
                {typeof value === "number" ? value.toLocaleString() : value}
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

function formatCurrency(n: number) {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}K`;
  return `$${n}`;
}

// Mock data — matches actual API types
const MOCK_SUMMARY: AnalyticsSummary = {
  contacts: 1_284,
  deals: 47,
  activities: 312,
  pipeline_value: 2_340_000,
  won_value: 890_000,
};

const MOCK_WIN_RATE: WinRate = {
  stages: {
    Prospecting: 340_000,
    Qualification: 520_000,
    Proposal: 680_000,
    Negotiation: 450_000,
    Closing: 350_000,
  },
  win_rate: 34.2,
  won: 18,
  lost: 35,
};

const MOCK_FORECAST: Forecast = {
  forecast: 360_000,
  breakdown: {
    Jul:  { raw: 165_000, weight: 0.9, weighted: 148_500 },
    Aug:  { raw: 198_000, weight: 0.9, weighted: 178_200 },
    Sep:  { raw: 225_000, weight: 0.85, weighted: 191_250 },
    Oct:  { raw: 260_000, weight: 0.8, weighted: 208_000 },
    Nov:  { raw: 320_000, weight: 0.7, weighted: 224_000 },
    Dec:  { raw: 360_000, weight: 0.6, weighted: 216_000 },
  },
};

const MOCK_ACTIVITIES: ActivityType[] = [
  { id: "a1", activity_type: "call",    description: "Follow-up call with Acme Corp",  contact_id: "c1", deal_id: "d1", created_at: new Date().toISOString() },
  { id: "a2", activity_type: "email",   description: "Sent proposal to GlobalTech",     contact_id: "c2", deal_id: "d2", created_at: new Date(Date.now() - 3_600_000).toISOString() },
  { id: "a3", activity_type: "meeting", description: "Demo with StartupXYZ team",       contact_id: "c3", deal_id: "d3", created_at: new Date(Date.now() - 7_200_000).toISOString() },
  { id: "a4", activity_type: "note",    description: "Updated pricing for Q4 deals",   contact_id: "c4", deal_id: null,  created_at: new Date(Date.now() - 10_800_000).toISOString() },
  { id: "a5", activity_type: "task",    description: "Prepare SOW for DataFlow Inc",   contact_id: "c5", deal_id: "d4", created_at: new Date(Date.now() - 14_400_000).toISOString() },
];

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
        setActivities(a.slice(0, 5));
      } catch {
        // Fallback to mock data for demo
        setSummary(MOCK_SUMMARY);
        setWinRate(MOCK_WIN_RATE);
        setForecast(MOCK_FORECAST);
        setActivities(MOCK_ACTIVITIES);
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
          value={formatCurrency(summary?.pipeline_value ?? 0)}
          icon={DollarSign}
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
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                    <XAxis dataKey="month" stroke="hsl(var(--muted-foreground))" fontSize={12} tickLine={false} />
                    <YAxis
                      stroke="hsl(var(--muted-foreground))"
                      fontSize={12}
                      tickLine={false}
                      tickFormatter={(v: number) => formatCurrency(v)}
                    />
                    <Tooltip
                      contentStyle={{
                        background: "hsl(var(--popover))",
                        border: "1px solid hsl(var(--border))",
                        borderRadius: "8px",
                        fontSize: "12px",
                      }}
                      labelStyle={{ color: "hsl(var(--foreground))" }}
                      formatter={(value: unknown) => [
                        formatCurrency(Number(value)),
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
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" horizontal={false} />
                    <XAxis
                      type="number"
                      stroke="hsl(var(--muted-foreground))"
                      fontSize={12}
                      tickLine={false}
                      tickFormatter={(v: number) => formatCurrency(v)}
                    />
                    <YAxis
                      dataKey="stage_name"
                      type="category"
                      stroke="hsl(var(--muted-foreground))"
                      fontSize={11}
                      tickLine={false}
                      width={90}
                    />
                    <Tooltip
                      contentStyle={{
                        background: "hsl(var(--popover))",
                        border: "1px solid hsl(var(--border))",
                        borderRadius: "8px",
                        fontSize: "12px",
                      }}
                      labelStyle={{ color: "hsl(var(--foreground))" }}
                      formatter={(value: unknown) => [
                        formatCurrency(Number(value)),
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
