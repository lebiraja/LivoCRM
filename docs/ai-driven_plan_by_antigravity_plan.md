# LivoCRM v2 — AI-Driven CRM Transformation

Transform LivoCRM from a traditional CRUD CRM into a **conversational, AI-first CRM** where the primary interface is a chat with an AI assistant that creates contacts, deals, and activities from natural language. Based on [ai-driven_plan.md](file:///home/lebi/projects/livocrm/docs/ai-driven_plan.md), adapted to the **actual stack** (FastAPI, SQLAlchemy, React + Zustand).

## User Review Required

> [!IMPORTANT]
> The vision doc assumes **Django + Channels + Anthropic Claude**. The actual codebase uses **FastAPI + SQLAlchemy + AWS Bedrock (Llama 4)**. This plan adapts all architecture to the real stack.

> [!WARNING]  
> **LLM Provider Decision** — The vision doc specifies Claude (Anthropic), but the existing backend already uses **AWS Bedrock** with Llama 4 Scout. This plan keeps **Bedrock** as the provider to avoid a new API key dependency and to reuse your existing AWS infra. The orchestrator prompts will work with any model — we can swap later if needed.

> [!IMPORTANT]
> **No existing tests** — There are zero unit/integration tests in the project. This plan adds pytest tests for the AI engine and chat flow. Frontend tests are deferred.

---

## Proposed Changes

### Phase 1 — AI Engine Core

Build the conversational AI brain: intent classification, entity extraction, follow-up question generation, and orchestration state machine.

---

#### [NEW] [orchestrator.py](file:///home/lebi/projects/livocrm/backend/app/services/ai_engine/orchestrator.py)

State machine managing the full conversation lifecycle:
- States: `IDLE → CLASSIFYING → COLLECTING → CONFIRMING → SAVING → COMPLETE`
- On each user message: classify intent → extract data → check completeness → ask follow-ups or present confirmation card
- Calls `intent_classifier`, `data_extractor`, `question_generator` internally
- Returns structured `OrchestratorResponse` with `ai_message`, `session_state`, `extracted_data`, `missing_fields`

#### [NEW] [intent_classifier.py](file:///home/lebi/projects/livocrm/backend/app/services/ai_engine/intent_classifier.py)

Classifies user messages into 8 intents using a single Bedrock call with structured JSON output:
`ADD_CONTACT`, `ADD_DEAL`, `LOG_ACTIVITY`, `UPDATE_CONTACT`, `UPDATE_DEAL`, `QUERY_DATA`, `GENERAL_CHAT`, `MULTI_INTENT`

#### [NEW] [data_extractor.py](file:///home/lebi/projects/livocrm/backend/app/services/ai_engine/data_extractor.py)

Extracts structured entity fields from natural language messages. Uses per-entity schemas (contact fields, deal fields, activity fields). Returns `ExtractedData` with `collected` and `missing_required` field lists.

#### [NEW] [question_generator.py](file:///home/lebi/projects/livocrm/backend/app/services/ai_engine/question_generator.py)

Generates natural, non-formulaic follow-up questions to fill missing required fields. Adapts tone based on conversation context. Never asks for fields already collected.

#### [NEW] [prompts.py](file:///home/lebi/projects/livocrm/backend/app/services/ai_engine/prompts.py)

All LLM prompt templates centralized in one file. System prompts for intent classification, extraction, question generation, and the main orchestrator persona.

#### [MODIFY] [bedrock_service.py](file:///home/lebi/projects/livocrm/backend/app/services/bedrock_service.py)

Add a generic `chat_completion(system_prompt, messages, max_tokens)` method that the AI engine modules can reuse, alongside the existing [get_insights()](file:///home/lebi/projects/livocrm/backend/app/services/bedrock_service.py#92-99) function. This avoids duplicating Bedrock client setup across files.

---

### Phase 2 — Chat Backend (Models + APIs)

New SQLAlchemy models, Alembic migration, Redis session management, and REST endpoints for the chat interface.

---

#### [NEW] [chat.py](file:///home/lebi/projects/livocrm/backend/app/models/chat.py) (models)

Three new models:
- **`ChatSession`** — `id`, `user_id` (FK→users), `title`, `state` (enum: IDLE/CLASSIFYING/COLLECTING/CONFIRMING/SAVING/COMPLETE), `intent`, `collected_data` (JSONB), `created_at`, `updated_at`
- **`ChatMessage`** — `id`, `session_id` (FK→chat_sessions), `role` (user/assistant/system), `content`, `metadata` (JSONB), `created_at`
- **`AIAction`** — `id`, `session_id` (FK→chat_sessions), `action_type` (created_contact/created_deal/logged_activity/updated_contact/updated_deal), `entity_id`, `entity_data` (JSONB), `created_at`

#### [NEW] [chat.py](file:///home/lebi/projects/livocrm/backend/app/schemas/chat.py) (schemas)

Pydantic schemas: `ChatSessionCreate`, `ChatSessionResponse`, `ChatMessageCreate`, `ChatMessageResponse`, `SendMessageRequest`, `SendMessageResponse`

#### [NEW] [chat.py](file:///home/lebi/projects/livocrm/backend/app/routers/chat.py) (router)

Endpoints:
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/chat/sessions/` | Create new session |
| `GET` | `/api/chat/sessions/` | List user's sessions |
| `GET` | `/api/chat/sessions/{id}` | Get session + messages |
| `DELETE` | `/api/chat/sessions/{id}` | Archive session |
| `POST` | `/api/chat/sessions/{id}/message` | Send message → get AI response |

#### [NEW] [session_manager.py](file:///home/lebi/projects/livocrm/backend/app/services/session_manager.py)

Redis-backed session cache with PostgreSQL fallback. Active sessions cached in Redis (TTL 7 days). On resume, loads from Redis first, falls back to DB.

#### [MODIFY] [contact.py](file:///home/lebi/projects/livocrm/backend/app/models/contact.py)

Add columns:
- `source VARCHAR(100) DEFAULT 'manual'` — tracks whether contact was created via AI chat or manually
- `ai_session_id UUID FK→chat_sessions` — links to the chat session that created it

#### [MODIFY] [deal.py](file:///home/lebi/projects/livocrm/backend/app/models/deal.py)

Add columns:
- `source VARCHAR(100) DEFAULT 'manual'`
- `ai_session_id UUID FK→chat_sessions`

#### [NEW] Alembic migration

Single migration file adding all new tables (`chat_sessions`, `chat_messages`, `ai_actions`) and the `source`/`ai_session_id` columns to [contacts](file:///home/lebi/projects/livocrm/backend/app/routers/contacts.py#17-31) and [deals](file:///home/lebi/projects/livocrm/backend/app/routers/deals.py#22-39).

#### [MODIFY] [docker-compose.yml](file:///home/lebi/projects/livocrm/docker-compose.yml)

Add Redis service:
```yaml
redis:
  image: redis:7-alpine
  ports:
    - "6379:6379"
  networks:
    - livocrm
```
Add backend dependency on `redis`.

#### [MODIFY] [requirements.txt](file:///home/lebi/projects/livocrm/backend/requirements.txt)

Add: `redis[hiredis]>=5.0.0`, `websockets>=12.0`

#### [MODIFY] [config.py](file:///home/lebi/projects/livocrm/backend/app/config.py)

Add `REDIS_URL` setting (already present but unused — wire it into session_manager).

#### [MODIFY] [main.py](file:///home/lebi/projects/livocrm/backend/app/main.py)

Register `chat_router` under `/api`.

---

### Phase 3 — Real-Time WebSocket

FastAPI-native WebSocket endpoints for live dashboard updates and chat typing indicators.

---

#### [NEW] [websocket.py](file:///home/lebi/projects/livocrm/backend/app/routers/websocket.py)

Two WebSocket endpoints:
- `ws://…/ws/dashboard/{user_id}` — pushes `dashboard_update` and `entity_created` events
- `ws://…/ws/chat/{session_id}` — pushes `ai_typing` indicator

Uses a simple in-memory connection manager (dict of `user_id → set[WebSocket]`). On entity create/update via AI, broadcasts to all user connections.

#### [NEW] [analytics_cache.py](file:///home/lebi/projects/livocrm/backend/app/models/analytics_cache.py)

`AnalyticsCache` model: `id`, `user_id` (UNIQUE FK→users), `dashboard_data` (JSONB), `pipeline_data` (JSONB), `forecast_data` (JSONB), `computed_at`

#### [NEW] [analytics_engine.py](file:///home/lebi/projects/livocrm/backend/app/services/analytics_engine.py)

`recompute_for_user(user_id)` — recalculates all dashboard metrics, updates cache, and pushes WebSocket event. Called after every AI-triggered DB write.

#### [MODIFY] [nginx.conf](file:///home/lebi/projects/livocrm/nginx/nginx.conf)

Add explicit `/ws/` location block with WebSocket proxy headers:
```nginx
location /ws/ {
    proxy_pass http://backend;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 86400s;
}
```

---

### Phase 4 — Frontend Chat Interface

Full chat UI with white-mode design system, Magic UI components, and WebSocket integration.

---

#### [MODIFY] [index.css](file:///home/lebi/projects/livocrm/frontend/src/index.css)

Complete rewrite with white-mode design tokens from the vision doc (Section 7.1). Replaces current dark theme variables.

#### [NEW] [ChatPage.tsx](file:///home/lebi/projects/livocrm/frontend/src/pages/ChatPage.tsx)

Three-column layout: sidebar (existing) → session list (280px) → active chat area. Full-height, no scroll on outer container.

#### [NEW] ChatPanel components

| File | Purpose |
|------|---------|
| `ChatInput.tsx` | Textarea + send button, Shift+Enter for newline, Enter to send |
| `ChatMessage.tsx` | Message bubble (user right, AI left), timestamp, markdown support |
| `ChatTypingIndicator.tsx` | Animated dots while AI processes |
| `ChatSessionList.tsx` | Scrollable session list with search, grouped by date |
| `ChatSessionCard.tsx` | Session card with status dot, entity badges, last message preview |
| `ConfirmationCard.tsx` | Structured summary card before save (name, email, company, etc.) |

#### [NEW] [chatStore.ts](file:///home/lebi/projects/livocrm/frontend/src/stores/chatStore.ts)

Zustand store: `sessions[]`, `activeSessionId`, `messages[]`, `isTyping`, `sendMessage()`, `createSession()`, `loadSessions()`

#### [NEW] [chat.ts](file:///home/lebi/projects/livocrm/frontend/src/api/chat.ts)

API client functions: `createSession()`, `listSessions()`, `getSession()`, `sendMessage()`, `archiveSession()`

#### [NEW] [useWebSocket.ts](file:///home/lebi/projects/livocrm/frontend/src/hooks/useWebSocket.ts)

WebSocket hook: connects to `/ws/dashboard/{userId}`, handles `dashboard_update` → invalidates TanStack Query cache, handles `entity_created` → shows toast.

#### [NEW] [useChat.ts](file:///home/lebi/projects/livocrm/frontend/src/hooks/useChat.ts)

Chat hook wrapping chatStore + WebSocket typing indicator. Manages send/receive lifecycle.

#### [MODIFY] [App.tsx](file:///home/lebi/projects/livocrm/frontend/src/App.tsx)

Add `/chat` route pointing to `ChatPage`.

---

### Phase 5 — Dashboard & Existing Pages Update

Add live indicators, AI source badges, and real-time updates to existing pages.

---

#### [MODIFY] Dashboard components

- Add `NumberTicker` animated counters for stats cards
- Add `LiveIndicator` pulsing dot component
- Add "Updated just now" badge with flash animation
- Wire WebSocket `dashboard_update` events to refresh stats

#### [MODIFY] Contacts page

- Add `SourceBadge` component showing "AI" or "Manual" per row
- "Add Contact" button now also shows "Add via Chat →" option

#### [MODIFY] Pipeline/Kanban page

- Show "Created via AI" badge on deal cards
- Real-time card appearance on WebSocket `entity_created` events

---

## Verification Plan

### Automated Tests

> [!NOTE]
> No tests currently exist. We'll add `pytest` + `pytest-asyncio` for backend testing.

**1. AI Engine unit tests** — `backend/tests/test_ai_engine.py`
```bash
cd /home/lebi/projects/livocrm/backend
pip install pytest pytest-asyncio httpx
pytest tests/test_ai_engine.py -v
```
Tests:
- Intent classifier returns valid intent enum for sample messages
- Data extractor produces correct JSON for known inputs (mocked Bedrock)
- Question generator omits already-collected fields
- Orchestrator state transitions: IDLE→CLASSIFYING→COLLECTING→CONFIRMING→COMPLETE

**2. Chat API integration tests** — `backend/tests/test_chat_api.py`
```bash
pytest tests/test_chat_api.py -v
```
Tests:
- Create session → 201, returns session_id
- Send message → 200, returns AI response with expected schema
- List sessions → returns only current user's sessions
- Archive session → 200, session no longer in list

**3. Migration verification**
```bash
cd /home/lebi/projects/livocrm/backend
alembic upgrade head
# Verify tables exist:
docker compose exec db psql -U livocrm_user -d livocrm -c "\dt chat_*"
# Should show: chat_sessions, chat_messages, ai_actions
docker compose exec db psql -U livocrm_user -d livocrm -c "\d contacts" | grep source
# Should show: source column
```

### Manual Verification

> [!TIP]
> These steps require Docker Compose running. Start with `docker compose up --build`.

**1. Full conversation flow** (after Phases 1-2):
1. Start the stack: `docker compose up --build`
2. Register/login via the frontend at `http://localhost:3500`
3. Open browser devtools → Network tab
4. Navigate to `/chat`
5. Click "New Conversation"
6. Type: "Just had a call with Arjun from Zeta Labs, his email is arjun@zeta.io"
7. Verify: AI responds asking for additional info (phone, deal, etc.)
8. Provide remaining info when asked
9. Verify: Confirmation card appears with all collected data
10. Confirm → verify toast "Contact saved" appears
11. Navigate to Contacts page → verify Arjun appears with "AI" source badge

**2. WebSocket live updates** (after Phase 3):
1. Open Dashboard in one browser tab
2. Open Chat in another tab
3. Create a contact via chat
4. Verify: Dashboard stats update without page refresh in the first tab

**3. UI/Design verification** (after Phase 4-5):
1. Open `http://localhost:3500` — verify white-mode theme
2. Chat page has 3-column layout
3. Send a message → verify typing indicator appears
4. Session list shows recent sessions with status dots
5. Dashboard cards animate on value change
