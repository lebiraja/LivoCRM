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
  /** How the contact was created: "manual" | "ai_chat" */
  source?: string | null;
  /** Chat session that created this contact, if any */
  ai_session_id?: string | null;
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
  /** How the deal was created: "manual" | "ai_chat" */
  source?: string | null;
  /** Chat session that created this deal, if any */
  ai_session_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface DealCreate {
  title: string;
  value: number;
  stage: DealStage;
  contact_id?: string;
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
export type ChatRole = "user" | "assistant";
export type WsStatus = "connecting" | "connected" | "disconnected";

export interface ChatSession {
  id: string;            // UUID
  title: string;
  status: string;        // "active" | "archived"
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface ChatMessage {
  id: string;          // UUID or temp id
  session_id: string;
  role: ChatRole;
  content: string;
  intent?: string | null;
  created_at: string;
}

/** Response from POST /chat/sessions/{id}/message */
export interface ChatSendResponse {
  session_id: string;
  user_message: ChatMessage;
  ai_message: ChatMessage;
  session_state: string;
  intent: string | null;
  extracted_data: Record<string, unknown>;
  missing_fields: string[];
  ready_to_save: boolean;
  session_title?: string | null;
}

/** A CRM action the AI wants permission to execute */
export interface AIActionPayload {
  /** e.g. "create_contact", "create_deal", "update_contact" */
  type: string;
  /** Human-readable entity name: "Contact", "Deal", … */
  entity: string;
  /** One-sentence description shown to the user */
  description: string;
  /** Structured data the action will use */
  data: Record<string, unknown>;
}

/** Pending confirmation card shown in the chat UI */
export interface ConfirmationRequest {
  /** Unique id for this pending confirmation (UUID or temp id) */
  id: string;
  action: AIActionPayload;
}
