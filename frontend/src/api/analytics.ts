import client from "./client";
import type { AnalyticsSummary, WinRate, Forecast, AIScoreResult } from "@/types";

export const analyticsApi = {
  /** GET /analytics/summary */
  getSummary: async (): Promise<AnalyticsSummary> => {
    const { data } = await client.get<AnalyticsSummary>("/analytics/summary");
    return data;
  },

  /** GET /analytics/win-rate */
  getWinRate: async (): Promise<WinRate> => {
    const { data } = await client.get<WinRate>("/analytics/win-rate");
    return data;
  },

  /** GET /analytics/forecast */
  getForecast: async (): Promise<Forecast> => {
    const { data } = await client.get<Forecast>("/analytics/forecast");
    return data;
  },

  /** GET /ai/score/{contact_id} */
  getLeadScore: async (contactId: string): Promise<AIScoreResult> => {
    const { data } = await client.get<AIScoreResult>(`/ai/score/${contactId}`);
    return data;
  },

  /** POST /ai/insights */
  getInsights: async (): Promise<{ insights: string[]; generated_by: string }> => {
    const { data } = await client.post<{ insights: string[]; generated_by: string }>(
      "/ai/insights"
    );
    return data;
  },

  // Legacy aliases — referenced in some pages under old names
  getDashboard: async (): Promise<AnalyticsSummary> => analyticsApi.getSummary(),
  getStageBreakdown: async (): Promise<WinRate> => analyticsApi.getWinRate(),
  getRevenueForecast: async (): Promise<Forecast> => analyticsApi.getForecast(),
  getAILeadScore: async (contactId: string): Promise<AIScoreResult> =>
    analyticsApi.getLeadScore(contactId),
};
