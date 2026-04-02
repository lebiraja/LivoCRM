# Frontend Documentation

## 1. Stack and Libraries
- React 19 + TypeScript
- Vite build tooling
- React Router
- Zustand state management
- Axios for HTTP
- Framer Motion for UI animation
- Recharts for charting
- Tailwind CSS + shadcn-style primitives

## 2. Application Shell
Files:
- `frontend/src/main.tsx`
- `frontend/src/App.tsx`
- `frontend/src/components/layout/Layout.tsx`
- `frontend/src/components/layout/Sidebar.tsx`
- `frontend/src/components/layout/TopBar.tsx`
- `frontend/src/components/shared/CommandMenu.tsx`

Behavior:
- `main.tsx` mounts app and global toaster.
- `App.tsx` defines route tree.
- `Layout` renders persistent sidebar + topbar and nested page outlet.
- Sidebar supports collapsed/expanded mode and logout action.
- Command menu opens with `Cmd/Ctrl+K` and provides navigation shortcuts.

## 3. Routes
Defined in `frontend/src/App.tsx`:
- `/` -> `DashboardPage`
- `/contacts` -> `ContactsPage`
- `/pipeline` -> `PipelinePage`
- `/settings` -> `SettingsPage`
- fallback `*` -> redirect `/`

Additional pages exist but are not currently routed:
- `LoginPage.tsx`
- `RegisterPage.tsx`

## 4. State Management

### 4.1 Auth Store (`frontend/src/stores/authStore.ts`)
State:
- `user`
- `isAuthenticated`
- `isLoading`

Actions:
- `login`
- `register`
- `fetchUser`
- `logout`
- `setUser`

Token handling:
- Uses `localStorage` keys:
- `access_token`
- `refresh_token`

### 4.2 UI Store (`frontend/src/stores/uiStore.ts`)
State:
- `sidebarOpen`
- `sidebarCollapsed`
- `commandOpen`

Actions control layout and command palette visibility.

## 5. API Client Layer
Files in `frontend/src/api/`:
- `client.ts`
- `auth.ts`
- `contacts.ts`
- `deals.ts`
- `activities.ts`
- `analytics.ts`

`client.ts`:
- Base URL from `VITE_API_URL` default `http://localhost:8000/api`.
- Request interceptor injects Bearer token.
- Response interceptor clears tokens and redirects to `/login` on HTTP 401.

## 6. Page-Level Behavior

### 6.1 Dashboard (`DashboardPage.tsx`)
- Loads dashboard KPIs, stage breakdown, revenue forecast, and recent activities.
- Uses chart components (`AreaChart`, `BarChart`).
- Falls back to in-file mock data when API calls fail.

### 6.2 Contacts (`ContactsPage.tsx`)
- Contact listing with search and selection.
- Create/edit dialog and bulk delete workflow.
- AI summary action per contact.
- Uses pagination controls.
- Falls back to mock contact data on API failure.

### 6.3 Pipeline (`PipelinePage.tsx`)
- Kanban-style deal board grouped by stage.
- Drag-and-drop to move deals across stages.
- Deal creation dialog.
- Falls back to mock stages/deals when APIs fail.

### 6.4 Settings (`SettingsPage.tsx`)
- Local-only profile, notification, appearance, and security preferences.
- No persisted backend integration currently.

## 7. Design System and Styling
File: `frontend/src/index.css`

- Custom design tokens via CSS variables.
- Dark-first visual system with glass and glow utilities.
- Fonts loaded from Geist CDN (`Geist`, `Geist Mono`).
- Tailwind v4 imports and custom utility classes.

## 8. Frontend-Backend Contract Gaps (Important)
Current frontend types and API calls are not yet aligned with backend contracts.

- Auth API mismatch:
- Frontend calls `/users/login/`, `/users/register/`, `/users/me/`.
- Backend exposes `/api/auth/login`, `/api/auth/register`, `/api/auth/me`.

- Data shape mismatch:
- Frontend types use numeric IDs and fields like `first_name`, `last_name`, `owner`.
- Backend returns UUIDs and fields like `name` (contact), `user_id`.

- Pagination mismatch:
- Frontend expects `PaginatedResponse<T>` envelopes.
- Backend list routes return plain arrays.

- Pipeline mismatch:
- Frontend expects pipeline stage CRUD endpoints (`/pipeline/stages/*`).
- Backend currently has model/schemas but no pipeline router endpoints.

- Route mismatch:
- Sidebar/command menu include `/analytics` route.
- `App.tsx` does not define `/analytics` page route.

## 9. Frontend Build and Run
- Dev: `cd frontend && npm install && npm run dev`
- Build: `cd frontend && npm run build`
- Docker image built via `frontend/Dockerfile`, served by Nginx.
