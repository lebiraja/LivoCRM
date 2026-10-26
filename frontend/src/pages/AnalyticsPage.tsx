import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  Users,
  Handshake,
  IndianRupee,
  TrendingUp,
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
import type {
  AnalyticsSummary,
  WinRate,
  Forecast,
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

function StatCard({
  title,
  value,
  icon: Icon,
  color,
}: {
  title: string;
  value: number | string;
  icon: React.ElementType;
  color: string;
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

export default function AnalyticsPage() {
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [winRate, setWinRate] = useState<WinRate | null>(null);
  const [forecast, setForecast] = useState<Forecast | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadAnalytics = async () => {
      setLoading(true);
      try {
        const [summaryData, winRateData, forecastData] = await Promise.all([
          analyticsApi.getSummary(),
          analyticsApi.getWinRate(),
          analyticsApi.getForecast(),
        ]);
        setSummary(summaryData);
        setWinRate(winRateData);
        setForecast(forecastData);
      } catch {
        toast.error("Failed to load analytics");
      } finally {
        setLoading(false);
      }
    };
    loadAnalytics();
  }, []);

  const winRateData = winRate
    ? Object.entries(winRate.stages).map(([stage, count]) => ({
        stage,
        count,
      }))
    : [];

  const forecastData = forecast
    ? Object.entries(forecast.breakdown).map(([stage, data]) => ({
        stage,
        raw: data.raw,
        weighted: data.weighted,
      }))
    : [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Analytics</h1>
        <p className="mt-2 text-muted-foreground">
          Track your CRM performance and pipeline health
        </p>
      </div>

      {/* KPI Cards */}
      {loading ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-5">
          {Array.from({ length: 5 }).map((_, i) => (
            <Card key={i}>
              <CardContent className="p-5">
                <Skeleton className="mb-4 h-4 w-24" />
                <Skeleton className="h-8 w-32" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : summary ? (
        <motion.div
          className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-5"
          variants={container}
          initial="hidden"
          animate="show"
        >
          <StatCard
            title="Total Contacts"
            value={summary.contacts}
            icon={Users}
            color="#3B82F6"
          />
          <StatCard
            title="Open Deals"
            value={summary.deals}
            icon={Handshake}
            color="#10B981"
          />
          <StatCard
            title="Pipeline Value"
            value={formatINR(summary.pipeline_value)}
            icon={IndianRupee}
            color="#F59E0B"
          />
          <StatCard
            title="Won Value"
            value={formatINR(summary.won_value)}
            icon={TrendingUp}
            color="#06B6D4"
          />
          <StatCard
            title="Activities"
            value={summary.activities}
            icon={Sparkles}
            color="#8B5CF6"
          />
        </motion.div>
      ) : null}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Win Rate Funnel */}
        {loading ? (
          <Card>
            <CardHeader>
              <Skeleton className="h-6 w-40" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-80" />
            </CardContent>
          </Card>
        ) : winRate && winRateData.length > 0 ? (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>Deal Stage Funnel</span>
                <Badge variant="outline">
                  {winRate.win_rate.toFixed(1)}% Win Rate
                </Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={350}>
                <BarChart data={winRateData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis type="number" />
                  <YAxis dataKey="stage" type="category" width={100} />
                  <Tooltip />
                  <Bar dataKey="count" fill="#3B82F6" radius={[0, 8, 8, 0]}>
                    {winRateData.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={STAGE_COLORS[index % STAGE_COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        ) : null}

        {/* Revenue Forecast */}
        {loading ? (
          <Card>
            <CardHeader>
              <Skeleton className="h-6 w-40" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-80" />
            </CardContent>
          </Card>
        ) : forecast && forecastData.length > 0 ? (
          <Card>
            <CardHeader>
              <CardTitle>
                Revenue Forecast: {formatINR(forecast.forecast)}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={350}>
                <AreaChart data={forecastData}>
                  <defs>
                    <linearGradient id="colorWeighted" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#3B82F6" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="stage" />
                  <YAxis />
                  <Tooltip />
                  <Area
                    type="monotone"
                    dataKey="weighted"
                    stroke="#3B82F6"
                    fillOpacity={1}
                    fill="url(#colorWeighted)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        ) : null}
      </div>
    </div>
  );
}
