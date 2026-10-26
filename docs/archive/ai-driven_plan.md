# LivoCRM v2 — AI-Driven CRM Transformation Plan
### From Static Forms → Conversational AI-First CRM

> This document is the complete implementation plan for transforming LivoCRM from a static form-based CRM into a fully dynamic, AI-driven system. The core shift: **users no longer fill forms — they talk to the system in natural language, and AI does the rest.**

---

## Table of Contents

1. [Vision & Core Shift](#1-vision--core-shift)
2. [System Architecture Overview](#2-system-architecture-overview)
3. [AI Interaction Design](#3-ai-interaction-design)
4. [Conversation Flow & State Machine](#4-conversation-flow--state-machine)
5. [Backend Changes](#5-backend-changes)
6. [Database Schema Changes](#6-database-schema-changes)
7. [Frontend Redesign](#7-frontend-redesign)
8. [Session Management](#8-session-management)
9. [Real-Time Analytics Pipeline](#9-real-time-analytics-pipeline)
10. [UI Component Plan](#10-ui-component-plan)
11. [API Design](#11-api-design)
12. [Folder Structure](#12-folder-structure)
13. [Implementation Phases](#13-implementation-phases)
14. [Verification Plan](#14-verification-plan)

---

## 1. Vision & Core Shift

### What changes

| Before (v1) | After (v2) |
|---|---|
| User fills static forms | User types in natural language |
| AI is only in analytics | AI drives the entire workflow |
| Predefined fields | AI dynamically asks follow-up questions |
| Data entry is manual | AI extracts and structures data from conversation |
| Dashboard is separate | Dashboard updates in real-time after every AI interaction |
| No chat history | Full session management with conversation continuity |
| Dark theme | Clean white mode with Magic UI + shadcn |

### The Core Loop

```
User types natural language
         │
         ▼
AI understands intent (contact / deal / lead / activity)
         │
         ▼
AI asks dynamic follow-up questions (conversational)
         │
         ▼
AI extracts structured data from the conversation
         │
         ▼
Data saved to PostgreSQL
         │
         ▼
Analytics recomputed in real-time
         │
         ▼
Dashboard updates instantly via WebSocket
```

### Example in Practice

```
User: "Just got off a call with Arjun from Zeta Labs,
       he's interested in our enterprise plan"

AI:   "Great! A few quick things to lock this in —
       what's Arjun's email and designation?"

User: "arjun@zetalabs.io, he's the CTO"

AI:   "Got it. What's the approximate deal value
       you're looking at, and when do you expect to close?"

User: "Around ₹2.5 lakhs, probably by end of May"

AI:   "Perfect. I've created Arjun's contact and opened
       a deal 'Enterprise Plan - Zeta Labs' at ₹2,50,000
       closing May 31. Lead score: 74. Want me to schedule
       a follow-up reminder?"
```

No forms. No dropdowns. Just conversation → structured data → live dashboard.

---

## 2. System Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React)                          │
│                                                                  │
│  ┌─────────────────────┐    ┌──────────────────────────────────┐ │
│  │   DASHBOARD VIEW    │    │        CHAT INTERFACE            │ │
│  │                     │◄───│  (Conversational AI Entry Point) │ │
│  │ Real-time analytics │    │  Session list | Active chat      │ │
│  │ Pipeline Kanban     │    │  Message history | Input bar     │ │
│  │ Contacts table      │    └──────────────┬───────────────────┘ │
│  └─────────────────────┘                   │                     │
└───────────────────────────────────────────┼─────────────────────┘
                                            │ WebSocket + REST
                                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                     BACKEND (Django)                             │
│                                                                  │
│  ┌──────────────┐  ┌─────────────────┐  ┌─────────────────────┐ │
│  │ Chat Router  │  │  AI Orchestrator│  │  Analytics Engine   │ │
│  │ /api/chat/   │─►│  (Core Brain)   │─►│  Real-time compute  │ │
│  └──────────────┘  └────────┬────────┘  └─────────────────────┘ │
│                             │                                    │
│               ┌─────────────┼─────────────┐                     │
│               ▼             ▼             ▼                     │
│  ┌────────────────┐ ┌──────────────┐ ┌──────────────────┐       │
│  │ Intent Detector│ │ Data Extractor│ │ Question Generator│       │
│  │ (classify msg) │ │ (NER + LLM)  │ │ (dynamic Q gen)  │       │
│  └────────────────┘ └──────────────┘ └──────────────────┘       │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    AI SERVICE LAYER                       │   │
│  │  Claude API (Anthropic) / AWS Bedrock                    │   │
│  │  Intent Classification | NER | Question Generation       │   │
│  │  Data Extraction | Lead Scoring | Summary Generation      │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
                            │
              ┌─────────────┼──────────────┐
              ▼             ▼              ▼
       ┌────────────┐ ┌──────────┐ ┌───────────────┐
       │ PostgreSQL │ │  Redis   │ │ Django Channels│
       │ (primary)  │ │ (session │ │ (WebSocket     │
       │            │ │  cache)  │ │  Server)       │
       └────────────┘ └──────────┘ └───────────────┘
```

---

## 3. AI Interaction Design

### 3.1 Intent Classification

Every user message is first classified into one of these intents:

| Intent | Example Trigger | Action |
|---|---|---|
| `ADD_CONTACT` | "Just met Priya from Infosys" | Start contact creation flow |
| `ADD_DEAL` | "Closed a deal with Ravi" | Start deal creation flow |
| `ADD_LEAD` | "Got a new lead from LinkedIn" | Start lead capture flow |
| `LOG_ACTIVITY` | "Had a call with Arjun today" | Log activity to existing contact |
| `UPDATE_DEAL` | "Moved the Zeta Labs deal to negotiation" | Update deal stage |
| `QUERY_DATA` | "How many deals did I close this month?" | Fetch and respond with analytics |
| `GET_INSIGHT` | "Who are my hottest leads right now?" | Run ML + return ranked list |
| `GENERAL` | "Thanks!" | Conversational response, no DB action |

### 3.2 Dynamic Question Generation

The AI does NOT ask predefined questions. It generates questions based on:
- What intent was detected
- What information was already provided in the message
- What fields are required for that entity in the DB
- What fields are optional but valuable

**System prompt structure for question generation:**

```
You are LivoCRM's AI assistant. Your job is to collect
structured CRM data through natural conversation.

Context:
- Intent detected: {intent}
- Already extracted from user message: {extracted_fields}
- Required fields still missing: {missing_required}
- Optional fields not yet collected: {missing_optional}
- Conversation history: {last_5_messages}

Generate ONE natural follow-up question or a maximum of
TWO questions grouped naturally. Be professional but warm.
Do not sound like a form. Never list all questions at once.
Never use bullet points in your questions.
```

### 3.3 Data Extraction

After each user response, the AI runs extraction:

```
You are a data extraction engine. Extract structured data
from the user's message.

Target schema: {json_schema_for_intent}
User message: "{user_message}"
Previously extracted: {already_collected}

Return ONLY valid JSON with extracted fields.
If a field cannot be confidently extracted, omit it.
Do not guess. Do not hallucinate values.
```

### 3.4 Conversation States

Each chat session has a state machine:

```
IDLE
  │ user sends message
  ▼
INTENT_DETECTED
  │ AI classifies intent
  ▼
COLLECTING (loop)
  │ AI asks question → user answers → AI extracts
  │ Loop until all required fields collected
  ▼
CONFIRMING
  │ AI summarizes what it will save: "Here's what I have..."
  │ User confirms or corrects
  ▼
SAVING
  │ Backend saves to PostgreSQL
  │ ML model recomputes lead score
  │ Analytics recomputed
  │ WebSocket pushes dashboard update
  ▼
COMPLETE
  │ AI confirms save + shows summary
  │ Offers next action (reminder, follow-up, related deal)
  ▼
IDLE (ready for next input)
```

### 3.5 Confirmation Before Save

Before writing to DB, AI always confirms:

```
AI: "Got it! Here's what I'll save:

  Contact: Arjun Mehta
  Company: Zeta Labs
  Email: arjun@zetalabs.io
  Role: CTO
  Deal: Enterprise Plan — ₹2,50,000
  Expected Close: May 31, 2026
  Lead Score: 74 (High)

  Shall I go ahead and save this?"
```

User says "yes" / "looks good" / "save it" → DB write happens.

---

## 4. Conversation Flow & State Machine

### 4.1 Session Object (Redis)

```json
{
  "session_id": "uuid",
  "user_id": "uuid",
  "title": "Arjun Mehta - Zeta Labs",
  "intent": "ADD_DEAL",
  "state": "COLLECTING",
  "collected_data": {
    "contact_name": "Arjun Mehta",
    "company": "Zeta Labs",
    "email": "arjun@zetalabs.io",
    "role": "CTO"
  },
  "required_fields_remaining": ["deal_value", "expected_close"],
  "optional_fields_remaining": ["phone", "tags", "notes"],
  "messages": [
    {"role": "user", "content": "...", "timestamp": "..."},
    {"role": "assistant", "content": "...", "timestamp": "..."}
  ],
  "created_at": "2026-04-02T10:00:00Z",
  "last_active": "2026-04-02T10:05:00Z"
}
```

### 4.2 Message Processing Pipeline

```
Incoming message from user
         │
         ▼
1. Load session from Redis
         │
         ▼
2. Append user message to session.messages
         │
         ▼
3. If state == IDLE:
   → Run intent classification
   → Set session.intent + session.state = COLLECTING
         │
         ▼
4. If state == COLLECTING:
   → Run data extraction on latest message
   → Merge into session.collected_data
   → Check required_fields_remaining
   → If empty → move to CONFIRMING
   → Else → generate next question
         │
         ▼
5. If state == CONFIRMING:
   → Parse user confirmation (yes/no/correction)
   → If confirmed → move to SAVING
   → If correction → update collected_data, re-confirm
         │
         ▼
6. If state == SAVING:
   → Write to PostgreSQL
   → Trigger ML lead score recompute
   → Trigger analytics recompute
   → Push WebSocket event to frontend
   → Move state to COMPLETE
         │
         ▼
7. Save updated session to Redis
         │
         ▼
8. Return AI response to frontend
```

---

## 5. Backend Changes

### 5.1 New Django Apps

Add these new apps to the existing Django project:

```
apps/
  chat/           ← NEW: chat sessions, message handling, AI orchestration
  ai_engine/      ← NEW: intent detection, extraction, question generation
  realtime/       ← NEW: Django Channels WebSocket consumers
```

Keep existing apps: `contacts/`, `deals/`, `activities/`, `pipeline/`, `analytics/`

### 5.2 New Dependencies

Add to `requirements.txt`:

```
# AI
anthropic>=0.25.0          # Claude API client
# OR
boto3>=1.34.0              # AWS Bedrock (if using Bedrock)

# Real-time
channels>=4.0.0            # Django Channels for WebSocket
channels-redis>=4.2.0      # Redis channel layer
daphne>=4.0.0              # ASGI server

# NLP / Processing
spacy>=3.7.0               # NER for entity extraction fallback

# Session
redis>=5.0.0               # Redis client
django-redis>=5.4.0        # Django Redis cache backend
```

### 5.3 New Services

#### `apps/ai_engine/intent_classifier.py`
```python
# Classifies user message into one of 8 intents
# Uses Claude API with structured output
# Returns: {intent, confidence, extracted_entities}
```

#### `apps/ai_engine/data_extractor.py`
```python
# Extracts structured fields from natural language
# Given intent + schema, returns populated JSON
# Handles: names, emails, phone numbers, dates, currency values
```

#### `apps/ai_engine/question_generator.py`
```python
# Given intent + collected_data + missing_fields
# Generates the next natural conversational question
# Returns: string (the AI's next message)
```

#### `apps/ai_engine/orchestrator.py`
```python
# Central brain — coordinates the full message processing pipeline
# Manages state transitions
# Calls intent_classifier → data_extractor → question_generator
# Triggers DB writes and analytics recompute
```

#### `apps/chat/session_manager.py`
```python
# CRUD for chat sessions in Redis
# load_session(session_id) → dict
# save_session(session_id, data)
# create_session(user_id) → session_id
# list_sessions(user_id) → [session summaries]
# get_session_history(session_id) → [messages]
```

#### `apps/realtime/consumers.py`
```python
# Django Channels WebSocket consumer
# Handles: dashboard_update events
# Pushes real-time analytics to connected frontend clients
# Group: user_{user_id}_dashboard
```

### 5.4 Modified Services

#### `apps/analytics/engine.py` — MODIFIED
- Add `recompute_for_user(user_id)` method
- Called after every successful DB write from AI
- Computes: total contacts, open deals, pipeline value, win rate, forecast
- Publishes result to WebSocket channel group

#### `apps/ai_engine/lead_scorer.py` — MODIFIED
- Now called automatically after contact/deal creation via AI
- Score stored immediately in Contact model
- Result included in AI confirmation message

### 5.5 ASGI Configuration

Replace `wsgi.py` with `asgi.py`:

```python
# livocrm_backend/asgi.py
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from apps.realtime.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})
```

---

## 6. Database Schema Changes

### 6.1 New Tables

#### `chat_sessions`
```sql
CREATE TABLE chat_sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    title           VARCHAR(255),
    intent          VARCHAR(100),
    state           VARCHAR(50) DEFAULT 'IDLE',
    is_archived     BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMP DEFAULT NOW(),
    last_active     TIMESTAMP DEFAULT NOW()
);
```

#### `chat_messages`
```sql
CREATE TABLE chat_messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role            VARCHAR(20) NOT NULL,   -- 'user' | 'assistant' | 'system'
    content         TEXT NOT NULL,
    intent          VARCHAR(100),
    extracted_data  JSONB,
    created_at      TIMESTAMP DEFAULT NOW()
);
```

#### `ai_actions`
```sql
CREATE TABLE ai_actions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      UUID REFERENCES chat_sessions(id),
    user_id         UUID REFERENCES users(id),
    action_type     VARCHAR(100) NOT NULL,  -- 'CREATE_CONTACT', 'CREATE_DEAL', etc.
    entity_id       UUID,
    entity_type     VARCHAR(50),            -- 'contact' | 'deal' | 'activity'
    input_data      JSONB,
    created_at      TIMESTAMP DEFAULT NOW()
);
```

#### `analytics_cache`
```sql
CREATE TABLE analytics_cache (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE UNIQUE,
    dashboard_data  JSONB NOT NULL,
    pipeline_data   JSONB NOT NULL,
    forecast_data   JSONB NOT NULL,
    computed_at     TIMESTAMP DEFAULT NOW()
);
```

### 6.2 Modified Tables

#### `contacts` — ADD COLUMNS
```sql
ALTER TABLE contacts ADD COLUMN source VARCHAR(100) DEFAULT 'chat';
ALTER TABLE contacts ADD COLUMN ai_session_id UUID REFERENCES chat_sessions(id);
ALTER TABLE contacts ADD COLUMN raw_input TEXT;
```

#### `deals` — ADD COLUMNS
```sql
ALTER TABLE deals ADD COLUMN source VARCHAR(100) DEFAULT 'chat';
ALTER TABLE deals ADD COLUMN ai_session_id UUID REFERENCES chat_sessions(id);
```

---

## 7. Frontend Redesign

### 7.1 Design System — White Mode

**Complete design token overhaul:**

```css
:root {
  /* Backgrounds */
  --bg-primary:     #FFFFFF;
  --bg-secondary:   #F8FAFC;
  --bg-tertiary:    #F1F5F9;
  --bg-hover:       #F0F4FF;

  /* Borders */
  --border-default: #E2E8F0;
  --border-focus:   #6366F1;
  --border-subtle:  #F1F5F9;

  /* Text */
  --text-primary:   #0F172A;
  --text-secondary: #475569;
  --text-muted:     #94A3B8;
  --text-accent:    #6366F1;

  /* Accents */
  --accent-primary: #6366F1;
  --accent-cyan:    #06B6D4;
  --accent-success: #10B981;
  --accent-warning: #F59E0B;
  --accent-danger:  #F43F5E;

  /* Chat specific */
  --chat-user-bg:   #EEF2FF;
  --chat-ai-bg:     #FFFFFF;
  --chat-ai-border: #E2E8F0;

  /* Shadows */
  --shadow-sm:   0 1px 2px rgba(0,0,0,0.05);
  --shadow-md:   0 4px 6px rgba(0,0,0,0.07);
  --shadow-lg:   0 10px 15px rgba(0,0,0,0.10);
  --shadow-card: 0 0 0 1px #E2E8F0, 0 2px 4px rgba(0,0,0,0.05);
}
```

**Typography:**
- UI: `Inter` (clean, readable)
- Numbers/metrics: `JetBrains Mono`
- AI messages: `Inter` with slightly looser line-height

**Magic UI components to use:**
- `AnimatedGradientText` — section headers and AI typing indicator
- `BorderBeam` — active chat session card highlight
- `ShimmerButton` — primary CTA buttons
- `MagicCard` — dashboard stat cards with hover gradient
- `AnimatedList` — activity feed items
- `BlurFade` — page transitions
- `NumberTicker` — animated metric counters on dashboard
- `Meteors` — subtle background on login/landing page
- `TypingAnimation` — AI response typing effect

### 7.2 Layout — Two-Panel

The app now has a permanent two-panel layout:

```
┌──────────────────────────────────────────────────────────────┐
│  SIDEBAR (240px)  │           MAIN CONTENT AREA              │
│                   │                                          │
│  Logo             │  ┌─────────────────────────────────────┐ │
│  Dashboard        │  │           TOP BAR                   │ │
│  Chat  ← NEW      │  └─────────────────────────────────────┘ │
│  Contacts         │                                          │
│  Pipeline         │  ┌───────────────┐  ┌──────────────────┐ │
│  Analytics        │  │  PAGE CONTENT │  │   CHAT PANEL     │ │
│  Settings         │  │               │  │  (persistent,    │ │
│                   │  │               │  │  collapsible,    │ │
│  User + Plan      │  │               │  │  380px wide)     │ │
└──────────────────────────────────────────────────────────────┘
```

Chat panel is always accessible — collapsed to floating button or expanded as right-side panel.

### 7.3 Pages

#### `/chat` — Chat Interface (NEW, PRIMARY PAGE)

```
┌──────────────────────────────────────────────────────────────┐
│ SIDEBAR (240px) │ SESSION LIST (280px) │  ACTIVE CHAT         │
│                 │                      │                      │
│  (nav)          │ Search sessions      │  [Session title]     │
│                 │ ─────────────────    │  ──────────────────  │
│                 │ + New Conversation   │                      │
│                 │ ─────────────────    │  AI: Hi! Tell me     │
│                 │ Today               │  about your latest   │
│                 │  Arjun - Zeta Labs  │  lead or update.     │
│                 │  Priya - Infosys    │                      │
│                 │ Yesterday           │  You: Just closed    │
│                 │  Enterprise deal    │  a deal with...      │
│                 │                     │                      │
│                 │                     │  AI: Great! A few    │
│                 │                     │  quick questions...  │
│                 │                     │  ─────────────────── │
│                 │                     │  [Type anything...]  │
│                 │                     │  [Send]              │
└──────────────────────────────────────────────────────────────┘
```

#### `/dashboard` — MODIFIED (Live Updates)

- Stats cards with `NumberTicker` animating on each WebSocket update
- Real-time badge: "Updated just now" with pulse dot
- WebSocket connection status indicator
- "Created via AI" tag on recent contacts/deals
- AI-generated insight panel: "3 deals haven't been touched in 7+ days"

#### `/contacts` — MODIFIED

- "Add Contact" form button replaced with "Add via Chat →"
- Each row shows `source` badge: `AI` or `Manual`
- Table data still fully sortable and filterable

#### `/pipeline` — MODIFIED

- Deals show "Created via AI" badge
- Stage changes can be triggered via chat: "Move Zeta Labs deal to negotiation"
- Kanban updates in real-time via WebSocket without page refresh

---

## 8. Session Management

### 8.1 Session Lifecycle

```
Create Session
│ POST /api/chat/sessions/
│ Returns: session_id, state: IDLE
▼
Active Conversation
│ POST /api/chat/sessions/{id}/message/
│ User sends → AI responds → state updates
│ Session title auto-generated from first entity
▼
Paused (user leaves)
│ Session persists in Redis (TTL: 7 days)
│ Full message history preserved
▼
Resumed
│ User opens old session from session list
│ History loaded from Redis (fallback: PostgreSQL)
│ AI: "Welcome back! We were discussing Arjun's deal —
│      shall we continue or start fresh?"
▼
Completed
│ After successful save → state: COMPLETE
│ Moved to recent sessions list
│ Viewable as read-only history
▼
Archived
│ Manual or auto-archived after 30 days
│ Stored only in PostgreSQL, removed from Redis
```

### 8.2 Session Continuity

When user resumes a session mid-flow, the AI receives this context:

```python
resume_context = {
    "session_state": session.state,
    "intent": session.intent,
    "collected_so_far": session.collected_data,
    "missing_required": session.missing_required,
    "last_3_messages": session.messages[-3:],
}
```

AI system prompt for resumed session:
```
The user is resuming a previous conversation.
State: {state}. We were collecting data for: {intent}.
Already collected: {collected_data}.
Still need: {missing_required}.
Greet them warmly and continue naturally from where we left off.
```

### 8.3 Session List UI

```
Completed Session Card:
┌─────────────────────────────────────┐
│  Arjun Mehta · Zeta Labs            │
│  Enterprise deal · ₹2,50,000        │
│  Saved 2 hours ago                  │
│  [Contact] [Deal]  ← entity badges  │
└─────────────────────────────────────┘

In-Progress Session Card:
┌─────────────────────────────────────┐
│  Priya Sharma · Infosys             │  ← yellow dot
│  Adding contact...                  │
│  Last active 5 min ago              │
└─────────────────────────────────────┘
```

Status dot colors: green = saved, yellow = in progress, grey = idle/abandoned

---

## 9. Real-Time Analytics Pipeline

### 9.1 Event Flow

```
AI saves entity to DB
         │
         ▼
analytics/engine.py → recompute_for_user(user_id)
         │
         ▼
Compute all dashboard metrics:
  - total_contacts   (COUNT)
  - open_deals       (COUNT WHERE status='open')
  - pipeline_value   (SUM of open deal values)
  - win_rate         (won / total closed * 100)
  - deals_by_stage   (GROUP BY stage)
  - revenue_forecast (SUM by expected_close month)
  - top_leads        (ORDER BY lead_score DESC LIMIT 10)
         │
         ▼
Update analytics_cache table for user
         │
         ▼
Publish to Django Channels group: user_{user_id}_dashboard
  Payload: { type: 'dashboard_update', data: {metrics} }
         │
         ▼
Frontend WebSocket receives event
         │
         ▼
TanStack Query cache invalidated → refetch triggered
         │
         ▼
Dashboard re-renders with new data
NumberTicker animates old value → new value
"Updated just now" badge flashes
```

### 9.2 WebSocket Events

```typescript
type DashboardUpdateEvent = {
  type: 'dashboard_update';
  data: {
    total_contacts: number;
    open_deals: number;
    pipeline_value: number;
    win_rate: number;
    deals_by_stage: { stage: string; count: number; value: number }[];
    top_leads: Contact[];
    computed_at: string;
  };
};

type EntityCreatedEvent = {
  type: 'entity_created';
  entity_type: 'contact' | 'deal' | 'activity';
  entity_id: string;
  summary: string;  // "New contact: Arjun Mehta (Zeta Labs)"
};

type ChatTypingEvent = {
  type: 'ai_typing';
  session_id: string;
  is_typing: boolean;
};
```

### 9.3 WebSocket Hook (Frontend)

```typescript
// src/hooks/useWebSocket.ts
const useWebSocket = (userId: string) => {
  const ws = useRef<WebSocket | null>(null);
  const queryClient = useQueryClient();

  useEffect(() => {
    ws.current = new WebSocket(
      `ws://localhost:8000/ws/dashboard/${userId}/`
    );

    ws.current.onmessage = (event) => {
      const payload = JSON.parse(event.data);

      if (payload.type === 'dashboard_update') {
        queryClient.invalidateQueries({ queryKey: ['analytics'] });
        queryClient.invalidateQueries({ queryKey: ['contacts'] });
        queryClient.invalidateQueries({ queryKey: ['deals'] });
      }

      if (payload.type === 'entity_created') {
        toast.success(payload.summary);
      }
    };

    return () => ws.current?.close();
  }, [userId]);
};
```

---

## 10. UI Component Plan

### New Components

```
ChatPanel/
  ChatPanel.tsx             ← collapsible right-side panel wrapper
  ChatInput.tsx             ← textarea with send button + shortcuts
  ChatMessage.tsx           ← single message bubble (user vs AI)
  ChatTypingIndicator.tsx   ← animated dots while AI processes
  ChatSessionList.tsx       ← left column session list
  ChatSessionCard.tsx       ← single session card in list
  ConfirmationCard.tsx      ← structured summary card before save
  EntityBadge.tsx           ← badge showing what was saved

Dashboard/
  LiveIndicator.tsx         ← pulsing green dot + "Live" text
  UpdatedBadge.tsx          ← "Updated just now" timestamp
  RealtimeStatsCard.tsx     ← MagicCard + NumberTicker combined
  InsightPanel.tsx          ← AI-generated insights section

shared/
  SourceBadge.tsx           ← "AI" or "Manual" badge on entities
  AIInsightPanel.tsx        ← glowing panel with AI recommendations
```

### Modified Components

- `StatsCard.tsx` — Add `NumberTicker` + `LiveIndicator` + flash on update
- `KanbanBoard.tsx` — Real-time deal appearance + "Created via AI" badge
- `Layout.tsx` — Add chat panel slot + floating chat button

---

## 11. API Design

### New Endpoints

```
POST   /api/chat/sessions/                  Create new chat session
GET    /api/chat/sessions/                  List user's sessions
GET    /api/chat/sessions/{id}/             Get session detail + messages
DELETE /api/chat/sessions/{id}/             Archive session
POST   /api/chat/sessions/{id}/message/     Send message, get AI response
GET    /api/chat/sessions/{id}/messages/    Get full message history

WS     /ws/dashboard/{user_id}/            Real-time dashboard updates
WS     /ws/chat/{session_id}/             Typing indicator stream

POST   /api/ai/classify/                   Classify intent of a message
POST   /api/ai/extract/                    Extract structured data from text
GET    /api/ai/insights/                   Get AI insights for current user
```

### Modified Endpoints

```
GET    /api/analytics/dashboard/    Now served from cache (instant response)
GET    /api/contacts/               Add ?source=ai filter
GET    /api/deals/                  Add ?source=ai filter
```

### Example: Message Endpoint

```json
POST /api/chat/sessions/abc-123/message/

Request:
{
  "content": "Just got off a call with Arjun from Zeta Labs"
}

Response:
{
  "message_id": "msg-uuid",
  "role": "assistant",
  "content": "Great! I can add Arjun as a new contact. What's his email and designation at Zeta Labs?",
  "session_state": "COLLECTING",
  "intent": "ADD_CONTACT",
  "extracted_so_far": {
    "name": "Arjun",
    "company": "Zeta Labs"
  },
  "missing_required": ["email"],
  "missing_optional": ["phone", "designation", "deal_info"]
}
```

---

## 12. Folder Structure

```
livocrm/
│
├── backend/
│   ├── livocrm_backend/
│   │   ├── settings.py        ← Add: CHANNEL_LAYERS, CACHES (Redis)
│   │   ├── urls.py            ← Add: chat, ai_engine routes
│   │   ├── asgi.py            ← NEW: replaces wsgi.py
│   │   └── routing.py         ← NEW: WebSocket URL routing
│   │
│   ├── apps/
│   │   ├── chat/              ← NEW
│   │   │   ├── models.py      ← ChatSession, ChatMessage, AIAction
│   │   │   ├── serializers.py
│   │   │   ├── views.py
│   │   │   ├── urls.py
│   │   │   └── session_manager.py
│   │   │
│   │   ├── ai_engine/         ← NEW
│   │   │   ├── orchestrator.py
│   │   │   ├── intent_classifier.py
│   │   │   ├── data_extractor.py
│   │   │   ├── question_generator.py
│   │   │   ├── lead_scorer.py
│   │   │   └── prompts.py
│   │   │
│   │   ├── realtime/          ← NEW
│   │   │   ├── consumers.py
│   │   │   └── routing.py
│   │   │
│   │   ├── analytics/         ← MODIFIED
│   │   │   ├── engine.py      ← Add recompute_for_user()
│   │   │   ├── models.py      ← Add AnalyticsCache
│   │   │   └── views.py
│   │   │
│   │   ├── contacts/          ← MODIFIED (source field)
│   │   ├── deals/             ← MODIFIED (source field)
│   │   ├── activities/
│   │   └── pipeline/
│   │
│   ├── ml/
│   │   ├── generate_data.py
│   │   └── train_scorer.py
│   │
│   └── requirements.txt       ← Add: anthropic, channels, daphne, spacy
│
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   ├── client.ts
│   │   │   ├── chat.ts        ← NEW
│   │   │   ├── contacts.ts
│   │   │   ├── deals.ts
│   │   │   ├── analytics.ts
│   │   │   └── auth.ts
│   │   │
│   │   ├── store/
│   │   │   ├── authStore.ts
│   │   │   ├── chatStore.ts   ← NEW
│   │   │   └── uiStore.ts
│   │   │
│   │   ├── hooks/
│   │   │   ├── useWebSocket.ts ← NEW
│   │   │   ├── useChat.ts      ← NEW
│   │   │   └── useAnalytics.ts ← NEW
│   │   │
│   │   ├── components/
│   │   │   ├── ChatPanel/      ← NEW
│   │   │   ├── Dashboard/      ← NEW live components
│   │   │   ├── Layout/         ← MODIFIED
│   │   │   ├── KanbanBoard/    ← MODIFIED
│   │   │   ├── ContactTable/   ← MODIFIED
│   │   │   ├── ActivityTimeline/
│   │   │   ├── LeadScoreBadge/
│   │   │   └── ui/
│   │   │
│   │   ├── pages/
│   │   │   ├── ChatPage.tsx        ← NEW
│   │   │   ├── DashboardPage.tsx   ← MODIFIED
│   │   │   ├── ContactsPage.tsx    ← MODIFIED
│   │   │   ├── PipelinePage.tsx    ← MODIFIED
│   │   │   ├── AnalyticsPage.tsx
│   │   │   ├── SettingsPage.tsx
│   │   │   ├── LoginPage.tsx
│   │   │   └── RegisterPage.tsx
│   │   │
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── globals.css             ← White mode design tokens
│   │
│   └── package.json
│
├── docker-compose.yml    ← MODIFIED: daphne, updated backend cmd
├── nginx/nginx.conf      ← MODIFIED: WebSocket proxy added
└── .env.example          ← Add: ANTHROPIC_API_KEY
```

---

## 13. Implementation Phases

### Phase 1 — AI Engine Backend (Week 1)
- [ ] Add `anthropic` package, configure Claude API client in `ai_engine/`
- [ ] Build `intent_classifier.py` — 8 intents, structured Claude output
- [ ] Build `data_extractor.py` — entity schemas for contact, deal, activity
- [ ] Build `question_generator.py` — dynamic, non-formulaic questions
- [ ] Build `orchestrator.py` — full state machine (IDLE → COMPLETE)
- [ ] Write unit tests for each component with real sample inputs

### Phase 2 — Chat Backend (Week 1-2)
- [ ] Create `chat` Django app
- [ ] Build `ChatSession`, `ChatMessage`, `AIAction` models + migrate
- [ ] Build `session_manager.py` (Redis CRUD + PostgreSQL fallback)
- [ ] Build chat views: create session, send message, list sessions
- [ ] Wire all URLs under `/api/chat/`
- [ ] Test full conversation flow end-to-end via curl/Postman

### Phase 3 — Real-Time WebSocket (Week 2)
- [ ] Install and configure Django Channels + daphne
- [ ] Replace `wsgi.py` with `asgi.py`
- [ ] Build WebSocket consumer in `realtime/consumers.py`
- [ ] Update `analytics/engine.py` with `recompute_for_user()`
- [ ] Create `AnalyticsCache` model
- [ ] Wire analytics recompute trigger after every AI-triggered DB write
- [ ] Update `docker-compose.yml` backend command to use daphne
- [ ] Update `nginx.conf` to proxy WebSocket connections
- [ ] Test WebSocket push events in browser devtools

### Phase 4 — Frontend Chat Interface (Week 2-3)
- [ ] Install Magic UI + update shadcn components
- [ ] Rewrite `globals.css` with white mode design tokens
- [ ] Build `ChatPage.tsx` — three-column layout
- [ ] Build all `ChatPanel/` components
- [ ] Build `chatStore.ts` (Zustand)
- [ ] Build `useChat.ts` and `useWebSocket.ts` hooks
- [ ] Wire chat UI