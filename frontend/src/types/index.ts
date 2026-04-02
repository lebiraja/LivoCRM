// ---------- User ----------
export interface User {
  id: string; // UUID
  email: string;
  full_name: string;
  is_active: boolean;
}

// Token returned by /auth/login
export interface AuthToken {
  access_token: string;
  token_type: string;
}

// ---------- Contact ----------
export interface Contact {
  id: string; // UUID
  name: string;
  email: string | null;
  phone: string | null;
  company: string | null;
  tags: string[];
  notes: string | null;
  lead_score: number | null;
  created_at: string;
  updated_at: string;
}

export interface ContactCreate {
  name: string;
  email?: string;
  phone?: string;
  company?: string;
  tags?: string[];
  notes?: string;
}

// ---------- Deal ----------
export type DealStatus = "active" | "won" | "lost";
export type DealStage =
  | "lead"
  | "qualified"
  | "proposal"
  | "negotiation"
  | "closed_won"
  | "closed_lost";

export interface Deal {
  id: string; // UUID
  title: string;
  value: number;
  stage: DealStage;
  status: DealStatus;
  contact_id: string;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface DealCreate {
  title: string;
  value: number;
  stage: DealStage;
  contact_id: string;
  notes?: string;
  status?: DealStatus;
}

// ---------- Activity ----------
export type ActivityType = "call" | "email" | "meeting" | "note" | "task";

export interface Activity {
  id: string; // UUID
  activity_type: ActivityType;
  description: string;
  contact_id: string;
  deal_id: string | null;
  created_at: string;
}

export interface ActivityCreate {
  activity_type: ActivityType;
  description: string;
  contact_id: string;
  deal_id?: string;
}

// ---------- Analytics ----------
export interface AnalyticsSummary {
  contacts: number;
  deals: number;
  activities: number;
  pipeline_value: number;
  won_value: number;
}

export interface WinRate {
  stages: Record<string, number>;
  win_rate: number;
  won: number;
  lost: number;
}

export interface Forecast {
  forecast: number;
  breakdown: Record<
    string,
    { raw: number; weight: number; weighted: number }
  >;
}

// ---------- AI ----------
export interface AIScoreResult {
  contact_id: string;
  score: number;
  label: string;
  features: Record<string, number>;
}

// Keep for legacy compatibility in any page that still uses it
export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

// Aliases kept so pages that reference old names don't hard-break
export type AuthTokens = AuthToken;
export type DashboardStats = AnalyticsSummary;
export type StageBreakdown = { stage_name: string; count: number; total_value: number };
export type RevenueForecast = { month: string; projected: number; actual: number };

// ---------- Chat ----------
export type ChatSource = "user" | "ai";
export type WsStatus = "connecting" | "connected" | "disconnected";

export interface ChatSession {
  id: string;            // UUID
  title: string;
  preview: string;
  created_at: string;
  updated_at: string;
}

export type AIActionType =
  | "create_contact"
  | "update_contact"
  | "create_deal"
  | "update_deal"
  | "log_activity"
  | "score_contact";

export interface AIAction {
  id: string;
  type: AIActionType;
  entity: string;       // e.g. "contact", "deal"
  fields: Record<string, unknown>;
  description: string;
}

export interface ConfirmationRequest {
  id: string;
  session_id: string;
  action: AIAction;
  created_at: string;
}

export interface ChatMessage {
  id: string;          // UUID or temp id
  session_id: string;
  source: ChatSource;
  content: string;
  confirmation?: ConfirmationRequest | null;
  created_at: string;
}
