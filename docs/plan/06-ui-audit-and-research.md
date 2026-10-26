# 06 - UI Audit and Research

**Purpose:** Current-state audit of the LivoCRM frontend plus cited research that feeds the redesign in `07-ui-redesign-plan.md`.
**Date:** 2026-10-26
**Status:** Draft v1 for Lebi's review (read-only audit; no source edited).
**Method:** Read all of `frontend/src` (pages, layout, chat, ui, magicui, stores, api, hooks, types), `index.css`, `index.html`, `vite.config.ts`, `package.json`, `Dockerfile`, `nginx.conf`, `docs/FRONTEND_DOCUMENTATION.md`, and the backend routers list. `node_modules` is not installed, so no build, bundle analysis or Lighthouse run was possible. Size and perf statements below are derived from the code and dependency list and marked [?] where not measured.

---

## 1. Route and screen inventory

| Route | File (lines) | Guard | What it shows | Data source |
|---|---|---|---|---|
| `/login` | `pages/LoginPage.tsx` (132) | PublicRoute | Centered "glass" form, Sparkles logo | `authStore.login` |
| `/register` | `pages/RegisterPage.tsx` (153) | PublicRoute | Same shell, 3 fields | `authStore.register` |
| `/` | `pages/DashboardPage.tsx` (409) | PrivateRoute + Layout | 4 stat cards, area chart, bar chart, "Recent Activity" list | `analyticsApi` x3 + `activitiesApi.list` |
| `/contacts` | `pages/ContactsPage.tsx` (568) | same | Search, card-per-row list, checkbox bulk delete, pagination (20), add/edit dialog, floating "AI Insight" popup | `contactsApi`, `analyticsApi.getInsights` |
| `/pipeline` | `pages/PipelinePage.tsx` (325) | same | 6-column HTML5 drag-and-drop kanban, create-deal dialog | `dealsApi` |
| `/chat` | `pages/ChatPage.tsx` (128) | same | Session list + message pane + input + confirmation card | `useChat` (REST) + `useWebSocket` |
| `/analytics` | `pages/AnalyticsPage.tsx` (289) | same | 5 stat cards (duplicate component), funnel bar, forecast area | `analyticsApi` x3 |
| `/settings` | `pages/SettingsPage.tsx` (435) | same | 4 tabs (profile, notifications, appearance, security), local state only | none |
| `*` | `App.tsx` | - | Redirect to `/` | - |

Not present: contact detail page, deal detail page, activity timeline per lead, follow-up/task queue, reports export, i18n.

## 2. Component inventory

| Area | Files | Notes |
|---|---|---|
| Layout | `Layout`, `Sidebar` (155), `TopBar` (52) | Sidebar is `fixed`, 240/72 px, animated with Framer Motion; no mobile variant |
| Shared | `CommandMenu` (cmdk), `ErrorBoundary` | CommandMenu has no Chat entry; quick-action `?action=new` query params are never read by pages |
| Chat | `ChatMessage`, `ChatInput`, `ChatSessionList`, `ChatTypingIndicator`, `ConfirmationCard` | Hard-coded Tailwind palette colours (amber, gray, violet) bypass tokens |
| shadcn `ui/` | 25 files | Imported by pages: alert-dialog, avatar, badge, button, card, command, dialog, input, label, separator, skeleton, sonner, tooltip. **No import outside `components/ui/`:** calendar, dropdown-menu, input-group, popover, progress, scroll-area, select, sheet, sidebar (702 lines), table, tabs, textarea |
| magicui | `AiTypingDots`, `LiveIndicator`, `NumberTicker`, `SourceBadge` | **All four unused** by any page. `NumberTicker` does not animate (it only sets a CSS variable). Chat has its own separate typing indicator |
| Dead code | `frontend/tmp-scaffold/` (own package.json, lock file 2,970 lines, README, src) | Vite scaffold leftover, not referenced. **Delete.** `src/assets/hero.png`, `react.svg`, `vite.svg`, `App.css` (184 lines, duplicate of scaffold) also unused [?: confirm with grep before deleting] |
| Dependencies unused in code | `@fontsource-variable/inter`, `geist` (fonts are loaded from jsDelivr CDN instead), `react-day-picker` (only via unused calendar), `shadcn` (CLI package placed in `dependencies`) | |

## 3. State flow

```
localStorage("access_token")
   |  read at module load
   v
authStore (zustand): isAuthenticated, user      axios client (api/client.ts)
   | login -> authApi.login -> token -> getMe       - Bearer interceptor
   | fetchUser on App mount                          - 401 -> remove token + hard
   v                                                   window.location redirect
PrivateRoute / PublicRoute                         (no refresh-token flow)

uiStore: sidebarOpen (unused), sidebarCollapsed, commandOpen   (not persisted)
chatStore: sessions, messages, pendingConfirmation, loading, streaming, wsStatus
   <- useChat (REST send; WS handler for ai_stream_start/ai_chunk/ai_message)
   <- useWebSocket (token in query string, max 5 retries)

Dashboard / Analytics / Contacts / Pipeline: local useState + useEffect fetch.
No shared cache, no request de-dup, no stale-while-revalidate, no refetch on focus.
```

Observations:
- Three pages fetch the same analytics endpoints independently (Dashboard and Analytics both call summary, win-rate, forecast) and re-fetch on every mount.
- `useChat.sendMessage` has an unused dependency list (`wsStatus`, `send`) and polls `listSessions` with a bare `setTimeout` after 3 s to pick up an async title.
- `sidebarOpen` / `toggleSidebar` exist but nothing reads them (leftover from an intended mobile drawer).
- `Pipeline` stage list is a hard-coded `STAGE_DEFS` array even though the backend exposes `/pipeline-stages`.
- Deal and contact references display raw UUIDs (`Contact {id}` on the dashboard, `deal.contact_id` on kanban cards).

## 4. Findings

Severity: **S1** breaks the grading demo or a real use case, **S2** clearly visible polish/quality gap, **S3** minor.

### 4.1 Visual system and consistency

| # | Sev | Finding | Evidence |
|---|---|---|---|
| V1 | S1 | **Dark mode is broken.** Settings toggles the `dark` class, and `@custom-variant dark` exists, but `index.css` has no `.dark { ... }` token block. Result: toggling dark changes nothing (or only partly via `dark:` utilities inside ui/ files). Settings also defaults its local state to `"dark"` while the app renders light. | `index.css` (only `:root`), `SettingsPage.tsx:38` |
| V2 | S1 | **Login/Register use classes that do not exist**: `mesh-gradient`, `glass`. The auth screens are unstyled shells. | `LoginPage.tsx:30,41`, `RegisterPage.tsx:40,50` |
| V3 | S1 | **Recharts colours are invalid.** Charts use `hsl(var(--border))` but the tokens are hex values, so grid lines, axis text and tooltip backgrounds fall back to defaults or render wrongly. Analytics charts use no theme colours at all. | `DashboardPage.tsx:255-290` |
| V4 | S2 | Indigo/violet/cyan default AI-SaaS look: indigo primary `#6366F1`, `gradient-text`, violet-to-indigo gradient avatars, radial hover glows. Directly against Lebi's brief (no blue gradients, no generic SaaS card grids). | `index.css`, `ChatMessage.tsx`, `ChatPage.tsx`, `DashboardPage.tsx StatCard` |
| V5 | S2 | Card grid everywhere: 4 KPI cards (Dashboard), 5 KPI cards (Analytics), card-per-contact rows. `StatCard` is copy-pasted in two pages with different colours (`#6366F1` vs `#3B82F6`). | `DashboardPage.tsx:62`, `AnalyticsPage.tsx:46` |
| V6 | S2 | Hard-coded colours bypass tokens: amber/white confirmation card, `text-gray-500`, `#3B82F6`, `STAGE_COLORS` arrays duplicated in 3 files. | `ConfirmationCard.tsx`, `ChatPage.tsx`, pages |
| V7 | S2 | Typography: Geist is fetched from jsDelivr at runtime (extra DNS + request on the critical path), while `geist` and `@fontsource-variable/inter` are installed but unused. `index.html` title is `frontend`. Page titles are inconsistent (`text-2xl` vs `text-3xl`). Tiny `text-[10px]` labels in many places. | `index.css:7-20`, `index.html`, `AnalyticsPage.tsx:129` |
| V8 | S2 | Currency is hard-coded to `$` and `K/M` abbreviation (Analytics even appends `k` to `pipeline_value`, which Dashboard formats differently). For Tamil Nadu clinics the unit should be INR with lakh/crore grouping. | `DashboardPage.tsx formatCurrency`, `PipelinePage.tsx`, `AnalyticsPage.tsx:183` |
| V9 | S3 | Four different loading/empty patterns (skeleton rows, centered text, dashed card, none). Analytics hides a chart entirely when data is empty. | pages |

### 4.2 Responsive

| # | Sev | Finding | Evidence |
|---|---|---|---|
| R1 | S1 | **No mobile navigation.** Sidebar is `fixed` at 240 px and `Layout` adds `marginLeft: 240` on every viewport; at 375 px the content area is about 135 px wide. `use-mobile.ts` and `ui/sheet.tsx` exist but nothing uses them. | `Layout.tsx:16`, `Sidebar.tsx` |
| R2 | S1 | **Kanban is unusable on touch.** HTML5 `draggable` has no touch support on mobile browsers; there is no "move to stage" menu or keyboard path. | `PipelinePage.tsx:204` |
| R3 | S2 | Contact rows cram avatar, name, tags, company, email, phone, score and actions on one line (no wrap/stack rules); row actions are `opacity-0 group-hover`, so invisible and unreachable on touch. | `ContactsPage.tsx` rows |
| R4 | S2 | TopBar shows full name + email at all widths; search is a read-only input that opens the command palette (a shortcut hint `Cmd K` is meaningless on phones). | `TopBar.tsx` |
| R5 | S2 | Chat: fixed 256 px session list always visible, `h-[calc(100vh-4rem)]` ignores mobile browser dynamic toolbar (`dvh`), bubbles `max-w-[75%]`. | `ChatPage.tsx`, `ChatSessionList.tsx` |
| R6 | S3 | Dialogs are fine on `sm:` but forms use 2-column grids that stay 2-column at 320 px. | `PipelinePage.tsx`, `ContactsPage.tsx` |

### 4.3 Accessibility

| # | Sev | Finding | Evidence |
|---|---|---|---|
| A1 | S1 | **Zero `aria-*` / `sr-only` attributes in pages, layout, chat and shared** (grep count 0). Icon-only buttons (sparkles, edit, send, new chat, sidebar collapse, show password) have no accessible name. | `grep` across `pages components/layout components/chat components/shared` |
| A2 | S1 | Kanban drag is mouse-only; no keyboard alternative, no live-region announcement of the move. | `PipelinePage.tsx` |
| A3 | S2 | Row checkboxes are bare `<input>` without labels; row "click" target is a `Card` with `cursor-pointer` but no handler or role. | `ContactsPage.tsx` |
| A4 | S2 | Colour-only meaning: lead score is green/amber/red text only; connection state uses icon colour plus text (OK). | `ContactsPage.tsx getScoreColor` |
| A5 | S2 | Contrast risks: `text-muted-foreground #64748B` on `#F8FAFC` ok (about 4.6:1) but `text-[10px]` copy is too small; `text-emerald-500` on white is about 2.5:1 (fails 4.5:1 for text). Values to be re-verified after token rewrite [?: not machine-measured in the current UI]. | `PipelinePage.tsx` value text, `getScoreColor` |
| A6 | S2 | No skip link, no `<main>` landmark label, no focus management on route change, `lang="en"` fixed, no `prefers-reduced-motion` handling although Framer Motion animates almost every page mount (stagger, layout, spring). | `index.html`, all pages |
| A7 | S3 | Touch targets: many `h-8 w-8` (32 px) icon buttons. WCAG 2.2 SC 2.5.8 (AA) only requires 24 px, so they pass, but 44 px is the usable target on a phone. | `ContactsPage.tsx` |

### 4.4 Tamil / i18n readiness

| # | Sev | Finding |
|---|---|---|
| I1 | S1 | **No i18n layer.** All copy is inline English in JSX (about 250 strings across 8 pages + chat). No message catalogue, no locale store. |
| I2 | S1 | **No Tamil font.** Geist/Inter do not cover Tamil, so Tamil text would fall back to whatever the OS has (Latha/Nirmala/Noto at random), with inconsistent weight and line-height. |
| I3 | S2 | Layouts assume short English labels: `whitespace-nowrap` on nav labels, `max-w-[80px] truncate`, `text-[10px]` badges, 4-up stat grids with fixed heights. Tamil strings are typically longer and taller (stacked vowel signs), so truncation and clipped line-heights are likely. |
| I4 | S2 | Dates use `toLocaleTimeString([])` (browser locale), numbers `toLocaleString()` without explicit locale; no `en-IN` grouping (12,34,567). |
| I5 | S3 | `Intl`, `date-fns` is installed (v4) but only English locale would be used by default; `date-fns/locale/ta` exists but is not wired [?: verify export name when implementing]. |

### 4.5 States: loading / empty / error

| Screen | Loading | Empty | Error |
|---|---|---|---|
| Dashboard | Skeleton grid | Silently shows zeros on any failure (looks like "no data", hides outage) | `console.error` only |
| Contacts | 5 skeleton rows | Dashed card + CTA (good) | Toast on load; **save errors are swallowed** ("In demo mode, just close"), delete failure falls back to local removal (lies to the user) |
| Pipeline | 6 skeleton columns | per-column dashed "Drop deals here" | `alert()` on create failure, silent reload on move failure |
| Chat | none visible | Hero "How can I help" (generic, gradient AI badge) | Assistant bubble with apology; WS drop shown only as "Offline" text |
| Analytics | skeleton | chart card disappears entirely | `console.error` only |
| Settings | n/a | n/a | "Saved!" label shown with **no API call** (fake save); profile hard-coded to "Lebi Raja", `America/*` time zones, no IST |

Also fabricated content in production code: a hard-coded "Sarah Johnson ... Acme Corp" AI summary used as an error fallback (`ContactsPage.tsx:189`). This must go; it presents invented data as insight.

### 4.6 Performance (derived, not measured)

| # | Finding | Impact |
|---|---|---|
| P1 | Single bundle: all 8 routes imported eagerly in `App.tsx`; recharts v3 (large) is bundled into the entry chunk although only Dashboard/Analytics use it. No `React.lazy`. | Larger first load; hurts LCP on a mid-range phone on 4G [?: size not measured] |
| P2 | Framer Motion used on layout width animation (`animate width/marginLeft`) which triggers layout every frame; `layout` prop on every contact row and deal card. | Jank on low-end devices |
| P3 | Fonts from CDN (render-blocking `@font-face` discovery after CSS) and no preload. | Extra connection + FOUT |
| P4 | No memoisation / virtualisation needed at current data volume (20 per page), but kanban filters the full deal array 2x per stage per render. | Minor now; relevant beyond a few hundred deals |
| P5 | Recharts `ResponsiveContainer` + 2 charts on the dashboard = heaviest paint. | Candidate for lazy chunk or replace with tiny inline SVG sparklines |

### 4.7 Documentation drift (affects grading)

`docs/FRONTEND_DOCUMENTATION.md` says Login/Register are "not currently routed", lists no `/chat` or `/analytics` routes and mentions a `refresh_token` that the code never stores. Update when the redesign lands (docs-keeper).

### 4.8 Top issues, ranked

1. No mobile navigation or touch-friendly pipeline (R1, R2).
2. Dark mode and auth screens broken/unstyled (V1, V2) plus invalid chart colours (V3).
3. Generic indigo "AI SaaS" look with repeated card grids, against Lebi's direction (V4, V5).
4. No i18n and no Tamil font (I1, I2) for the clinic demo audience.
5. Zero accessibility labelling and mouse-only drag (A1, A2), plus fake saves and swallowed errors (Section 4.5).

---

## 5. Research

All sources fetched on 2026-10-26. `[?]` = I could not verify the claim from a primary source in this session.

### 5.1 How modern minimal CRMs present data

| Product / source | What it does (verified) | Takeaway for LivoCRM |
|---|---|---|
| **Linear** design refresh, 2026-03-12: https://linear.app/blog/behind-the-latest-design-refresh | Principles: "don't compete for attention you haven't earned" and "structure should be felt, not seen". Sidebar dimmer with smaller icons and muted inactive text; fewer, softer separators; default themes moved from cool blue-ish to a warmer, less saturated gray; icon use reduced; coloured icon backgrounds removed; predictable header bar. | Warm neutral palette, receding chrome, hairlines over boxes. Directly supports "calm, minimal" and removing coloured KPI icon tiles. |
| **Linear** UI redesign, 2024-03-28: https://linear.app/now/how-we-redesigned-the-linear-ui | Theme generated from three inputs (base, accent, contrast) using LCH, instead of 98 variables; a contrast variable for accessible high-contrast themes; Inter Display for headings, Inter for body; focus on density and alignment of navigation. | Define tokens from few inputs; ship a high-contrast option; keep a single type family plus one display face. |
| **Attio** views help: https://attio.com/help/reference/managing-your-data/views | Records appear as spreadsheet-style **table** views or **kanban** views, with filter and sort. Grouping and saved views not confirmed on that page. | Table-first lead list with a kanban as an alternate view of the same data, not a separate product area. |
| **Pipedrive** pipeline help: https://support.pipedrive.com/en/article/pipeline-view | Cards show title, contact, value, label, owner (customisable); an **activity icon** on each card shows upcoming activities and lets you mark done or schedule; a **Rotting** feature highlights deals not updated recently; default sort is by next activity. Totals and move-drag behaviour not described on that page. | The most important thing on a pipeline card is "what is the next action and is it overdue", not the deal value. This maps exactly to follow-up tracking. |
| **Twenty CRM** (open source) README and user guide: https://twenty.com/user-guide/section/getting-started/what-is-twenty , https://github.com/twentyhq/twenty | Table and kanban views with filters, sort, group by, personalised layouts. Third-party mirrors list AGPL-3.0; install counts unverified. | Confirms the "one dataset, multiple views" model; Twenty is also a real-world reference for a shadcn-like React CRM. Do not copy code (AGPL). |
| **Folk**, **Close** | Not fetched. Commonly described as list-and-timeline CRMs with a call/email inbox focus. | [?] No claims used in the plan. |
| **Zoho Bahi-Khata** | No such Zoho product found. Search surfaced OkCredit's "bahi khata" app (https://okcredit.in/bahi-khata-app), described as a digital udhar ledger for micro and small businesses in 11 Indian languages, and Zoho Books localisation in Tamil/Hindi etc. (Zoho community post on language localisation). | Simplicity reference for Indian SMB: one ledger-like list per person, big tap targets, local-language UI. Treat "Zoho Bahi-Khata" in the brief as OkCredit/Khatabook-style. [?] OkCredit's exact UX not inspected. |

### 5.2 Standards used for acceptance criteria

| Topic | Source | Fact used |
|---|---|---|
| Text contrast | W3C WCAG 2.2 Understanding 1.4.3: https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html | AA: 4.5:1 normal text, 3:1 large text (18 pt, or 14 pt bold). |
| Target size | W3C What's New in WCAG 2.2: https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22 and DAISY KB summary of SC 2.5.8 | 24x24 CSS px minimum at AA (2.5.8) with spacing exception; 44x44 is the AAA level (2.5.5). Plan targets 44 px for primary touch controls. |
| Reduced motion | MDN `prefers-reduced-motion`: https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-reduced-motion | Keep default animation, override inside `@media (prefers-reduced-motion: reduce)`. Baseline widely available since January 2020. |
| Motion principles | Apple HIG Motion: https://developer.apple.com/design/human-interface-guidelines/motion (summary only was retrievable) | Purposeful, optional (never carry essential info), brief, respect Reduce Motion. |
| Core Web Vitals | web.dev: https://web.dev/articles/vitals | Good: LCP <= 2.5 s, INP <= 200 ms, CLS <= 0.1, judged at the 75th percentile. |
| Empty states | Nielsen Norman Group: https://www.nngroup.com/articles/empty-state-interface-design/ | Empty states should communicate system status (not flash "no records" while loading), provide learning cues, and give a direct pathway to the key task. |
| Breakpoints | Bootstrap 5.3 docs: https://getbootstrap.com/docs/5.3/layout/breakpoints/ | xs <576, sm 576, md 768, lg 992, xl 1200, xxl 1400; mobile-first via `min-width` queries. |
| Dark theme guidance | Material 3 dark theme page returned 404 at the URL tried. | [?] Not cited. Dark tokens in the plan are my own and verified only by computed contrast ratios (section 3 of plan 07). |

### 5.3 Tamil typography

| Fact | Source |
|---|---|
| Noto Sans Tamil is available as a variable font via Fontsource (`@fontsource-variable/noto-sans-tamil`, weights 100-900 plus a width axis), under the SIL OFL 1.1. 244 glyphs, 147 characters across five Unicode blocks. | https://fontsource.org/fonts/noto-sans-tamil/install , https://www.jsdelivr.com/package/npm/@fontsource-variable/noto-sans-tamil |
| Tamil needs complex-text-layout shaping by the platform. | https://fontsource.org/fonts/noto-sans-tamil/about |
| Recommendation to use a taller line-height for Tamil than Latin (about 1.6 vs 1.4-1.5). | Common practice, **[?] not confirmed from a primary source**; will be validated visually in Phase 0 with a Tamil sample page. |
| Fontsource install command and exact CSS import. | Page excerpt did not include the literal values [?]; follow the package README at install time. |

### 5.4 Not researched / gaps

- Chat/assistant UI patterns: no primary source fetched this session. The plan relies on first principles (assistant as an action panel, explicit confirmation before mutations, already present in `ConfirmationCard`) and on the existing backend behaviour. [?]
- Quantified benchmarks for Indian SMB mobile usage (device classes, network speeds): not sourced. The plan sets performance budgets conservatively instead.
- Folk, Close, Zoho CRM screens were not inspected directly.

## 6. Back-end dependencies discovered

The redesign needs a **follow-up queue** and **no-show / missed-lead** views. The backend currently has `contacts`, `deals`, `activities` (type `task` exists, but no `due_at`/`status` fields), `pipeline_stages`, `analytics`, `chat`, `ai`. Grep for `due`, `follow`, `remind`, `next_action` in `backend/app/models` and `schemas` finds nothing relevant. Phase 3 of plan 07 therefore lists a small backend change (due date and completed flag on activities, or `next_follow_up_at` on contacts) as an explicit dependency; the UI can ship first with the existing `task` activity type and client-side grouping of the activities list.
