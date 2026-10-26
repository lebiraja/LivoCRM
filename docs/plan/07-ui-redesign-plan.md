# 07 - UI Redesign Plan

**Purpose:** One committed design direction, design system, wireframes, component refactor list, phased checklist and acceptance criteria for the LivoCRM frontend redesign. Stack unchanged (React 19, Vite, TypeScript strict, Tailwind v4, shadcn/ui on Radix, Zustand, Recharts, Framer Motion, a few Magic UI pieces).
**Date:** 2026-10-26
**Status:** Draft v1 for Lebi's review. No code changed. Evidence and citations are in `06-ui-audit-and-research.md`.

---

## 1. Direction: "Ledger" (editorial minimal, warm paper and ink)

One sentence: LivoCRM looks like a well-kept paper register that tells you who to call today, calm warm neutrals, one deep-green accent, serif headlines, dense hairline-ruled lists instead of card grids, and the same layout working one-handed on a phone.

### Why this fits the product and the two users

| Need | Design answer |
|---|---|
| Clinic receptionist on a phone, interrupted constantly | Home is **Today**: a ranked follow-up list with one-tap call/WhatsApp and "done / snooze". No chart above the fold. Bottom nav, thumb-reach actions, 44 px targets. |
| Broker on a laptop with many leads | Dense table with keyboard navigation, saved filters, command palette, kanban as an alternate view of the same data. |
| Tamil + English | Typography chosen for Tamil first (taller line-height, Noto Sans Tamil), text-first layout that wraps instead of truncating, language toggle in the top bar. |
| Indian SMB trust | Ledger metaphor (rows, rules, totals) is familiar from bahi-khata style apps (see research 5.1). INR formatting with lakh/crore grouping. |
| Graded front-end marks (responsive, aesthetic, polished) | Strong, consistent identity; breakpoints mirror Bootstrap's set; every screen has loading, empty and error states. |
| Lebi's brief | No blue gradients, no card grids, no "Get Started" hero; shadcn customised as base; Magic UI only where it carries meaning. |

### Principles

1. **Today first.** The question is "who do I contact now?", not "how is the pipeline?".
2. **Rows, not boxes.** Structure by hairline rules and whitespace ("structure felt, not seen", Linear 2026). Cards only for modals/popovers/toasts.
3. **Chrome recedes.** Nav is quiet; content and the next action carry the colour.
4. **One accent, used for action only.** Status uses text + shape + colour, never colour alone.
5. **Tamil is a first-class script**, not a translation afterthought: no fixed heights, no `nowrap` on labels, no sub-12 px text.
6. **Honest UI.** No fake saves, no invented data, errors are shown (audit 4.5).
7. **Motion confirms, never decorates**; everything has a reduced-motion path.

---

## 2. Design system

### 2.1 Colour tokens

Defined as CSS variables on `:root` and `.dark` in `index.css` (shadcn token names kept so ui/ components keep working), mapped through `@theme inline`. Light is default; dark follows `prefers-color-scheme` until the user picks, then stored in `localStorage`. Ratios below were computed with the WCAG relative-luminance formula (script in session scratchpad), not eyeballed.

| Token | Light | Dark | Use |
|---|---|---|---|
| `--background` | `#FAF8F4` | `#161513` | App canvas |
| `--raised` (muted bg) | `#F1EEE7` | `#201F1C` | Table header, sheet, input fill |
| `--foreground` | `#1C1B18` | `#ECE9E2` | Body text |
| `--muted-foreground` | `#5F5B53` | `#A19D93` | Secondary text |
| `--border` (decorative hairline) | `#E4DFD3` | `#2E2C27` | Row rules (no contrast requirement) |
| `--input` (control border) | `#8C8A82` | `#8B877D` | Input/checkbox outlines (needs 3:1) |
| `--primary` (accent) | `#0F6B5C` | `#4FC3A9` | Primary button, links, focus ring, active nav |
| `--primary-foreground` | `#FFFFFF` | `#0B1F1B` | Text on accent |
| `--overdue` | `#A3411D` | `#F08A62` | Overdue follow-up, no-show |
| `--warning` | `#8A5A00` | `#E0B04A` | Due today, stale lead |
| `--success` | `#2E7D32` | `#6FCF8A` | Done, won |
| `--destructive` | `#B3261E` | `#F2766D` | Delete, error |
| `--ring` | `#0F6B5C` | `#4FC3A9` | 2 px focus ring, 2 px offset |

Measured contrast (WCAG 2.2 AA needs 4.5:1 text, 3:1 non-text/large text):

| Pair | Light | Dark |
|---|---|---|
| foreground on background | 16.24 | 15.05 |
| muted-foreground on background | 6.37 | 6.74 |
| muted-foreground on raised | 5.83 | 6.09 |
| primary-foreground on primary (button) | 6.41 | 7.92 |
| primary as text on background | 6.04 | 8.44 |
| overdue on background | 5.94 | 7.40 |
| warning on background | 5.59 | 9.11 |
| success on background | 4.83 | 9.53 |
| destructive on background | 6.16 | 6.59 |
| input border on background (non-text) | 3.26 | 5.09 |

Rejected: `#8C8A82` / `#7A766D` as text (3.26 / 4.27, fail). Stage colours: no rainbow. Pipeline stages use one hue ramp via opacity of `--primary` plus text label and a small position meter (e.g. `●●○○○`), so stage is readable in greyscale. Charts: one accent series, neutral comparison series, direct labels instead of legends. Recharts props must read `var(--...)` strings directly (the current `hsl(var(--x))` is invalid with hex tokens).

Provide a **high-contrast** attribute (`data-contrast="high"`) later (Phase 7 stretch) in the spirit of Linear's contrast variable.

### 2.2 Typography

| Role | Font | Notes |
|---|---|---|
| UI and body | Inter Variable (already a dependency) + **Noto Sans Tamil Variable** | Self-host via Fontsource, `font-display: swap`, subsets `latin` + `tamil`, preload the Latin 400-600 file. Remove the jsDelivr `@font-face` blocks. Stack: `"Inter Variable","Noto Sans Tamil Variable",system-ui,sans-serif` so Tamil glyphs always come from Noto, not a random OS font. |
| Display (page titles, big numbers) | Newsreader Variable (serif) falling back to **Noto Serif Tamil Variable** | Editorial identity. [?] Confirm both packages exist in Fontsource at install time; fallback is Inter 600 with tighter tracking (no new dependency). |
| IDs, phone numbers | `ui-monospace` (system) | Drop Geist Mono. Use `font-variant-numeric: tabular-nums` on Inter for money/counts. |

Scale (rem, 16 px base; inputs stay at 16 px so iOS does not zoom):

| Token | Size / line-height Latin | Tamil line-height | Use |
|---|---|---|---|
| `text-xs` | 12 / 1.4 | 1.65 | Meta only, never sole carrier of meaning |
| `text-sm` | 14 / 1.5 | 1.7 | Table cells, secondary |
| `text-base` | 16 / 1.55 | 1.7 | Body, inputs |
| `text-lg` | 18 / 1.45 | 1.65 | Row primary text on mobile |
| `text-xl` | 22 / 1.3 | 1.55 | Section title |
| `text-2xl` | 28 / 1.2 | 1.45 | Page title (serif) |
| `text-4xl` | 40 / 1.1 | 1.35 | Today count, KPI numerals (serif, tabular) |

Apply the Tamil line-heights with `:lang(ta)` selectors on `<html lang>`. Line-height values are my starting point [?] and must be checked on a Tamil specimen page in Phase 0 (Tamil stacked signs should not clip).

### 2.3 Spacing, radius, elevation

| Token | Value |
|---|---|
| Spacing | 4 px base; page gutter 16 px mobile, 24 px md, 32 px xl; row height 56 px mobile / 44 px desktop table |
| Radius | `--radius: 0.375rem` (6 px) for controls; 12 px for sheets/dialog; 0 for table rows; pills only for status chips |
| Elevation | None on content. One popover/menu shadow `0 4px 16px rgb(0 0 0 / .10)`; bottom nav and sticky header separated by a hairline, no blur |
| Layout max width | Content 1120 px, reading column (detail, settings) 680 px |

### 2.4 Iconography

lucide-react, 18 px, stroke 1.5, `currentColor`, always paired with a visible label in navigation and on primary actions (icon-only allowed only for close, overflow, call/WhatsApp with `aria-label`). No coloured icon tiles. Remove the `Sparkles` logo mark; wordmark "LivoCRM" in the display serif with a small solid accent dot.

### 2.5 Motion rules

| Rule | Value |
|---|---|
| Durations | 120 ms (hover, press), 200 ms (sheet, popover, route fade), 320 ms max (reorder) |
| Easing | `cubic-bezier(.2,.8,.2,1)` out; no springs on layout |
| Allowed | Route fade, sheet/dialog enter, toast, follow-up row collapse on "done", kanban drop settle, number count-in on Reports headline, assistant "thinking" dots |
| Forbidden | Staggered entrance on every page, hover glows, animating `width`/`margin` of layout, infinite animations other than the thinking dots |
| Reduced motion | Global `@media (prefers-reduced-motion: reduce)` sets durations to 0.01 ms and swaps slides for opacity; Framer `MotionConfig reducedMotion="user"` at root |
| Magic UI | Exactly two uses: real **NumberTicker** (Reports headline totals) and **AiTypingDots** (assistant). Delete `LiveIndicator`, `SourceBadge` (replace with a text "AI" tag), and the fake NumberTicker. |

---

## 3. Component rules

| Component | Rule |
|---|---|
| **Data table (Leads, desktop)** | shadcn `Table`, sticky header, 44 px rows, hairline rules, zebra none. Columns: Name (+phone), Status chip, Next follow-up (relative + absolute on hover), Source, Score, Owner. Row is a link to lead detail (`<a>` in the first cell, row click via CSS stretched link). Keyboard: `j/k` move, `Enter` open, `x` select, `/` focus search. Column visibility saved to `localStorage`. Bulk bar appears sticky at bottom when rows selected. |
| **Lead list (mobile)** | Same data as a ruled list: line 1 name (text-lg), line 2 next follow-up + status, right side a 44 px call button and WhatsApp button. No hover-only actions; overflow menu (`DropdownMenu`) for edit/delete. |
| **Pipeline board** | Desktop: columns as ruled lanes (no filled boxes), card = title, lead name, value, next-action line with overdue colour and "stale N days" (Pipedrive "rotting" idea, research 5.1). Drag with mouse AND a visible "Move to..." menu on every card (keyboard + touch). Announce moves through `aria-live="polite"`. Mobile: single-stage view with a horizontal stage tab strip (counts + totals); long-press not required. |
| **Lead detail timeline** | Header (name, status, call/WhatsApp, next follow-up with Done/Snooze). Body: reverse-chronological activity list on a vertical rule with a small marker per type (call, note, meeting, task, AI). Composer pinned at bottom (mobile) or top of the timeline (desktop): type chips + text + optional follow-up date. Sidebar facts on desktop only. |
| **Follow-up queue (Today)** | Grouped: Overdue, Today, Next 7 days. Each row: person, reason (from last activity), due time, actions (Call, WhatsApp, Done, Snooze 1 day / tomorrow / pick date). Done collapses the row (320 ms) and shows an Undo toast. |
| **Dashboard KPIs (no card grid)** | One typographic "status line" at top of Today: `4 overdue · 7 due today · 2 new this week` in the display serif. Reports page uses a single ruled **definition list** (label left, numeral right, delta text) and two charts; no coloured tiles. |
| **Assistant panel** | Desktop: right-hand drawer (`Sheet`, 420 px) available from every page via `A` shortcut and top-bar button; full page `/chat` kept for history. Mobile: full screen, bottom tab "Assistant". Messages: user right in `--raised`, assistant left plain text with no avatar gradient; a small `AI` text tag. Suggestions are 3 context-aware chips (follow-ups, missed leads, add lead). Mutations always show `ConfirmationCard` restyled with tokens (border-left in warning colour), buttons labelled with the verb ("Create lead Priya", not "Confirm"). Connection state: a dot + text, `role="status"`. |
| **Forms** | Labels above, 16 px inputs, 44 px height on mobile, helper and error text in `text-sm` linked with `aria-describedby`, `aria-invalid`. Use native `<select>`/`type="tel"`/`inputmode` on mobile for speed; shadcn `Select` on desktop only if needed. Validation with Zod at submit, errors per field; no `alert()`. Dialog becomes a bottom `Sheet` below `md`. |
| **Toasts** | sonner, bottom-center on mobile (above the bottom nav) and bottom-right on desktop; max 3; success auto-dismiss 4 s, errors persist until closed; Undo action where reversible. |
| **Modals** | Radix Dialog / AlertDialog (focus trap, Esc). Destructive confirmation names the object ("Delete 3 leads?") and lists what is lost. |
| **Empty states** | Per NN/g: say what this is, why it is empty, one direct action, never shown while loading. Example Leads: "No leads yet. Add your first lead or import a CSV." |
| **Loading** | Skeletons that match final row geometry (no layout shift); inline spinner only on buttons. |
| **Errors** | Inline banner at section level with Retry; never show zeros on failure (current dashboard behaviour). |

---

## 4. Navigation model

| Viewport | Pattern |
|---|---|
| `< 768 px` | Top bar (title, language toggle, theme, avatar menu) + **bottom nav, 5 items**: Today, Leads, Pipeline, Assistant, More (Reports, Settings, Log out in a bottom sheet). Active item: accent text + 2 px top rule. Safe-area padding `env(safe-area-inset-bottom)`. Add-lead FAB replaced by a persistent "+ Lead" action in the Leads header (avoids covering list content). |
| `768-1199 px` | Icon + label rail, 64 px, labels below icons (Tamil labels wrap to two lines max). |
| `>= 1200 px` | Left sidebar 208 px, text labels, quiet (muted inactive, no filled active pill: active = accent text + 2 px left rule). Collapse removed (the 72/240 animated width is the source of layout jank). |
| Everywhere | `Ctrl/Cmd+K` command palette (extend with Chat, Reports, leads search via API, "Add follow-up"); skip link; one `<main id="main">`; `<nav aria-label="Primary">`. |

Route changes:

| Old | New | Notes |
|---|---|---|
| `/` Dashboard | `/` **Today** | Follow-up queue + status line |
| `/contacts` | `/leads` (redirect from `/contacts`) | Table / list |
| - | `/leads/:id` | Lead detail + timeline (new) |
| `/pipeline` | `/pipeline` | Board (desktop), stage tabs (mobile) |
| `/chat` | `/assistant` (redirect from `/chat`) | Full page; also drawer |
| `/analytics` | `/reports` | Merged: Dashboard charts move here |
| `/settings` | `/settings` | Real profile (from `/auth/me`), language, theme, timezone IST |

Data model names stay (`Contact`, `Deal`) in code; only labels change ("Lead" for clinics: "Patient enquiry" as an optional industry label in Settings, Phase 6 stretch).

### Tamil / English toggle

- Control: segmented text button `தமிழ் | EN` in the top bar (mobile and desktop), also in Settings. Not a flag icon. Each segment has `lang` attribute and `aria-pressed`.
- Implementation without a new dependency: `src/i18n/` with `en.ts` as the source of truth (typed `as const` object), `ta.ts` typed as `Record<keyof typeof en, string>` so a missing key is a compile error; `useT()` hook reading a Zustand `localeStore` (`"en" | "ta"`, persisted); `t("leads.empty.title", { count })` with simple interpolation; pluralisation via `Intl.PluralRules`.
- Sets `document.documentElement.lang` and swaps font stack/line-height through `:lang(ta)`.
- Formatting: `Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 })` for both locales (Tamil Nadu convention uses Western digits with lakh grouping; `ta-IN` formatting available as a setting) [?: decide with Lebi]; dates via `Intl.DateTimeFormat(locale, ...)` and `date-fns` relative strings with `ta` locale where available [?].
- Layout rules: no `whitespace-nowrap` on labels, `min-w-0` + wrapping instead of truncation for names and reasons, `min-height` not `height`, test pages with a 1.4x text-length stress mode (`?pseudo=1` replaces strings with elongated text in dev).
- Translation workflow: Lebi supplies or reviews Tamil strings; machine-drafted Tamil is flagged `// TODO(review)` in `ta.ts`; clinic-specific vocabulary (follow-up = "தொடர் அழைப்பு"? ) must be reviewed by a native speaker [?]. Do not ship unreviewed Tamil to a client.
- Backend/AI: assistant replies stay in the language the user types; pass `locale` in the chat request (backend change, optional).

---

## 5. Wireframes

Legend: `[ ]` button, `(o)` selected, `---` hairline rule, `>` row link.

### 5.1 Today (`/`)

Desktop (>= 1200)

```
+-----------+--------------------------------------------------------------+
| LivoCRM . |  Today                         [Search lead  Ctrl K] [தமிழ|EN] [A] |
|           |  Thursday, 26 Oct                                            |
| Today     |                                                              |
| Leads     |  3 overdue  .  6 due today  .  2 new this week     (serif 40)|
| Pipeline  |  ----------------------------------------------------------- |
| Assistant |  OVERDUE                                                     |
| Reports   |  Priya Raman      Asked price for scan, no reply 3 days      |
|           |                   was due Mon 10:00   [Call] [WhatsApp] [Done] [Snooze v]
|           |  ----------------------------------------------------------- |
|           |  Karthik S        Missed appointment (no-show) Tue           |
|           |                   was due Tue 16:00   [Call] [WhatsApp] [Done] [Snooze v]
| Settings  |  TODAY                                                       |
| Log out   |  Meena Devi       Reschedule dental cleaning   11:30  ...    |
|           |  ...                                                         |
|           |  NEXT 7 DAYS (collapsed, 9)  [Show]                          |
+-----------+--------------------------------------------------------------+
```

Mobile (375)

```
+--------------------------------+
| LivoCRM .       [தமிழ|EN] [A]  |
+--------------------------------+
| 3 overdue . 6 today . 2 new    |
| ------------------------------ |
| OVERDUE                        |
| Priya Raman                    |
| Asked price, no reply 3 days   |
| was due Mon          [Call][WA]|
| [Done]  [Snooze v]             |
| ------------------------------ |
| Karthik S         no-show      |
| ...                            |
+--------------------------------+
| Today  Leads  Pipe  Assist More|
+--------------------------------+
```

Empty: "Nothing due. Nice. Add a follow-up from any lead, or ask the assistant to find leads with no reply." + [Add lead].

### 5.2 Leads (`/leads`)

Desktop

```
Leads  (248)                                    [Import CSV] [+ Add lead]
[Search name or phone]  Status: All v   Source: All v   Due: Any v   [Saved: Missed leads v]
-----------------------------------------------------------------------------------------
[ ] Name              Status        Next follow-up     Source       Score   Owner
-----------------------------------------------------------------------------------------
[ ] Priya Raman       Enquiry       Overdue 3d (red)   WhatsApp      82      Anitha  >
    98400 12345
[ ] Karthik S         No-show       Tue 16:00          Walk-in       64      Anitha  >
...
-----------------------------------------------------------------------------------------
Showing 1-20 of 248                                         [< Prev]  1 / 13  [Next >]
```

Mobile

```
Leads (248)            [+ Lead]
[Search...........] [Filters 2]
--------------------------------
Priya Raman               [Call]
Enquiry . overdue 3 days   [WA]
--------------------------------
Karthik S                 [Call]
No-show . Tue 16:00        [WA]
--------------------------------
         [Load more]
```

Filters open a bottom sheet. Selection mode via long-press or "Select" in overflow.

### 5.3 Lead detail (`/leads/:id`)

Desktop

```
< Leads
Priya Raman                         [Call] [WhatsApp] [Edit] [...]
Enquiry . Score 82 . WhatsApp . Added 12 Oct
Next follow-up: Mon 23 Oct 10:00 (overdue 3 days)  [Done] [Snooze v] [Change]
---------------------------------------------------------------------------
Timeline                                    |  Details
[Call][Note][Visit][Task]  [ write note.. ] |  Phone  98400 12345
[ ] Follow-up on [date v]        [Save]     |  Email  -
---------------------------------------------|  Tags   scan, price
 o  Today 09:12  AI  Suggested: send price list|  Deals  Full body scan  Rs 6,500 >
 |  Mon 23 Oct   Call - no answer              |
 |  Fri 20 Oct   Note - asked price for scan   |
 o  12 Oct       Lead created from WhatsApp    |
```

Mobile: header, then sticky action row (Call, WhatsApp, Done), sections as in-page tabs `Timeline | Details | Deals`; composer sticks above bottom nav.

### 5.4 Pipeline (`/pipeline`)

Desktop

```
Pipeline        Rs 12.4 L open . 18 deals              [Board|List]  [+ Deal]
  ENQUIRY (6)  Rs 2.1 L   | BOOKED (4)  Rs 3.0 L   | VISITED (3)  Rs 4.2 L  | WON (5) | LOST (2)
  ------------------------|------------------------|------------------------|
  Full body scan          | Dental cleaning        | Root canal             |
  Priya R.   Rs 6,500     | Meena D.   Rs 1,200    | Arun K.   Rs 9,000     |
  Overdue 3d (red)        | Today 11:30            | Stale 9 days (amber)   |
  [Move to v]             | [Move to v]            | [Move to v]            |
  ------------------------|                        |                        |
```

Mobile

```
Pipeline                [+ Deal]
[Enquiry 6][Booked 4][Visited 3][Won][Lost]   <- scrollable tab strip, active underlined
Rs 2.1 L in this stage
--------------------------------
Full body scan          Rs 6,500
Priya R.  . overdue 3 days
[Move to v]
--------------------------------
```

Stage labels come from `/pipeline-stages` (API) with an editable name in Settings, not the hard-coded array.

### 5.5 Assistant (`/assistant` and drawer)

```
Desktop drawer (420)                  Mobile (full screen)
+-----------------------------+       +------------------------------+
| Assistant   . connected  [x]|       | < Assistant       . connected|
|-----------------------------|       |------------------------------|
| You: who hasn't replied?    |       | You: who hasn't replied?     |
| AI: 3 leads, oldest 5 days: |       | AI: 3 leads...               |
|   Priya R., Karthik S., ... |       |                              |
| +- Confirm ---------------+ |       | + Create follow-up for 3? -+ |
| | Create follow-up for 3? | |       | | [Create 3 follow-ups]    | |
| | [Create 3] [Dismiss]    | |       | +--------------------------+ |
| +-------------------------+ |       | [Who is overdue?][Add lead]  |
| [Overdue?][Add lead][Missed]|       | [ message........... ] [Send]|
| [ message......... ] [Send] |       +------------------------------+
+-----------------------------+       (bottom nav hidden here)
```

Sessions list: a "History" button opens a sheet; no permanent 256 px column.

### 5.6 Reports (`/reports`)

```
Reports                                  Period: Last 30 days v
-----------------------------------------------------------------
Leads added            48     +12 vs previous
Follow-ups completed   132    91 percent on time
Missed (no reply 7d+)  9      -3
Won value              Rs 3.4 L
-----------------------------------------------------------------
Leads by stage (horizontal bars, labels inline, one colour)
Forecast (line, weighted vs raw, direct labels)
[Export CSV]
```

Mobile: same list, charts below, each chart has a data table fallback (`<details>`).

### 5.7 Settings (`/settings`) and Auth

```
Settings (680 px column, sections on one page, in-page anchors on desktop)
Profile (from /auth/me) | Language (தமிழ/EN) | Appearance (Light/Dark/System)
| Time zone (IST default) | Pipeline stage names | Notifications | Security | Log out

Login (centered column, no glass, no gradient)
  LivoCRM .                  [தமிழ|EN]
  Sign in
  Email    [______________]
  Password [______________] (show)
  [Sign in]      Create an account
  Demo clinic: use demo@... (only in demo build) [?]
```

---

## 6. Component refactor list

| Action | Item | Detail |
|---|---|---|
| **Delete** | `frontend/tmp-scaffold/` | Entire directory (dead scaffold, own lockfile) |
| Delete | `src/App.css`, `src/assets/{hero.png,react.svg,vite.svg}` | Unreferenced (confirm with grep first) |
| Delete | `components/magicui/{LiveIndicator,SourceBadge,NumberTicker}` | Replace NumberTicker with the real Magic UI implementation |
| Delete | `components/ui/{sidebar,calendar,input-group,progress,scroll-area,popover}` | Unused (re-add via shadcn CLI if needed later); drop `react-day-picker` |
| Delete | `uiStore.sidebarOpen/toggleSidebar` | Unused |
| Delete | npm deps `geist`, `shadcn` (move CLI to devDeps or `npx`) | Fonts switch to Fontsource |
| **Merge** | `StatCard` x2, `formatCurrency` x3, `STAGE_COLORS` x3 | Into `lib/format.ts` (`formatINR`, `formatRelative`) and `StatusLine`/`MetricList` components |
| Merge | `DashboardPage` + `AnalyticsPage` | Into `ReportsPage`; Dashboard becomes `TodayPage` |
| Merge | `ChatTypingIndicator` + `AiTypingDots` | One component `ThinkingDots` |
| **Restyle** | `button`, `input`, `textarea` (replace raw `<textarea>`/`<select>` in pages), `badge` (status chip), `dialog` (bottom sheet on mobile), `table`, `tabs`, `sonner` | Token-driven; 44 px min height on touch |
| Restyle | `ChatMessage`, `ChatInput`, `ConfirmationCard`, `ChatSessionList` | Tokens only, no gradients/hard-coded colours; session list becomes a sheet |
| Restyle | `CommandMenu` | Add Chat/Reports/lead search/add follow-up; remove dead `?action=new` links or implement them |
| Restyle | `ErrorBoundary` | Token styling, Retry + "Report" link, i18n |
| Restyle | `LoginPage`, `RegisterPage` | Remove `mesh-gradient`/`glass`; plain centered column |
| **New** | `AppShell` (replaces `Layout`, `Sidebar`, `TopBar`) with `BottomNav`, `SideNav`, `TopBar`, `SkipLink` | Responsive nav model |
| New | `LanguageToggle`, `ThemeToggle`, `i18n/` (en, ta, `useT`, `localeStore`) | |
| New | `FollowUpRow`, `FollowUpGroup`, `SnoozeMenu` | Today + lead detail |
| New | `LeadTable`, `LeadList`, `LeadFilters` (+ `FilterSheet`), `StatusChip`, `CallButton`/`WhatsAppButton` (`tel:` and `https://wa.me/<number>` links) | |
| New | `LeadDetailPage`, `Timeline`, `TimelineItem`, `ActivityComposer` | Needs `contactsApi.get` (exists) + activities filter by `contact_id` [?: confirm backend filter param] |
| New | `StageTabs`, `DealCard`, `MoveToMenu`, `useBoardDnd` (HTML5 DnD kept, plus menu path) | Replaces inline kanban in `PipelinePage` |
| New | `AssistantDrawer` (uses `Sheet`), `SuggestionChips` | Reuses `useChat` |
| New | `EmptyState`, `ErrorState`, `SkeletonRows` | One pattern for all screens |
| New | `lib/api-schemas.ts` (Zod at API boundary) and `lib/queries.ts` | Zod per Lebi's convention; optional small fetch cache hook (`useResource`) to de-dup analytics calls without adding a new dependency |
| New | `routes.tsx` with `React.lazy` per route and Suspense skeletons | Splits recharts into the Reports chunk |
| Fix | `SettingsPage` | Wire profile to `/auth/me`; remove fake "Saved!"; drop hard-coded name; IST |
| Fix | `ContactsPage` | Remove demo fallbacks and the invented "Sarah Johnson" summary; surface real errors |
| Fix | `PipelinePage` | Remove `alert()`; use `/pipeline-stages`; revert on failed move with toast |

---

## 7. Phased task list

Estimates are for Lebi working solo with Claude agents; hours include self-review. Total about 75 h (about 9 working days).

### Phase 0 - Foundation and cleanup (6 h)
- [ ] (0.5 h) Delete `tmp-scaffold/`, unused assets, unused ui files and deps; `npm run build` still passes
- [ ] (1.5 h) Rewrite `index.css`: tokens (light + `.dark`), `@theme inline` mapping, remove dead utilities, Bootstrap-aligned breakpoints (`--breakpoint-sm: 36rem; md: 48rem; lg: 62rem; xl: 75rem; 2xl: 87.5rem`)
- [ ] (1 h) Self-hosted fonts (Inter, Noto Sans Tamil, display serif), preload, `:lang(ta)` line-heights; Tamil specimen page checked visually
- [ ] (1 h) `index.html`: title, `lang`, meta description, theme-color (light + dark), favicon, no-FOUC dark script
- [ ] (1 h) `ThemeToggle` + persisted theme; `MotionConfig reducedMotion="user"`; global reduced-motion CSS
- [ ] (1 h) Install vitest + @testing-library/react + jest-dom + Playwright; scripts `test`, `test:e2e`; one smoke test each
- Acceptance: `tsc -b && vite build` clean; dark toggle changes whole UI; Tamil sample renders in Noto Sans Tamil with no clipped glyphs at 320 px.

### Phase 1 - App shell and navigation (6 h)
- [ ] (3 h) `AppShell`, `BottomNav`, `SideNav`, `TopBar`, `SkipLink`, `LanguageToggle`; route renames with redirects (`/contacts`, `/chat`, `/analytics`)
- [ ] (1 h) `React.lazy` route splitting + skeleton fallbacks
- [ ] (1 h) Extend `CommandMenu`; fix dead quick actions
- [ ] (1 h) i18n scaffold (`en.ts`, `ta.ts` type-checked, `useT`, `localeStore`, `Intl` helpers `formatINR`, `formatDate`)
- Acceptance: nav works at 320, 375, 768, 1024, 1280, 1440 with no horizontal scroll; keyboard-only navigation reaches every item; bottom nav respects safe-area; initial JS (gzip) under 180 KB [?: measure baseline in Phase 0 and set final budget].

### Phase 2 - Today, Leads, Lead detail (14 h)
- [ ] (2 h) `EmptyState`, `ErrorState`, `SkeletonRows`, `StatusChip`
- [ ] (4 h) `LeadsPage`: table (desktop) + list (mobile), URL-synced search/filters, pagination, bulk delete with real error handling, call/WhatsApp links
- [ ] (4 h) `LeadDetailPage` + `Timeline` + `ActivityComposer`
- [ ] (4 h) `TodayPage` with `FollowUpGroup/Row`, snooze/done with optimistic update + Undo (uses `task` activities until Phase 3 backend lands)
- Acceptance: all four states (loading, empty, error, data) have a vitest test per page; Lead row actions reachable on touch; no UUIDs shown to users; Done/Snooze are keyboard accessible.

### Phase 3 - Pipeline and follow-up data (12 h)
- [ ] (4 h) Backend (via `implementer`, with tests): `due_at` + `completed_at` (or `status`) on activities, and `GET /activities/?due_before=&status=`; Alembic migration; update `docs/API.md`/schema docs. Dependency flagged to Lebi: this is the only non-frontend work in the plan.
- [ ] (4 h) `PipelinePage` board with `/pipeline-stages`, `DealCard`, `MoveToMenu`, a11y live region, optimistic move with rollback toast
- [ ] (2 h) Mobile `StageTabs` view
- [ ] (2 h) Stale/overdue indicators on cards
- Acceptance: a deal can be moved by mouse, keyboard and touch; failure reverts and toasts; pipeline renders 200 deals without dropped frames (manual check, Performance panel).

### Phase 4 - Assistant (6 h)
- [ ] (2 h) `AssistantDrawer` + restyled `ChatMessage/Input/ConfirmationCard`; sessions as sheet; `dvh` heights
- [ ] (1 h) Context chips; labelled confirm buttons
- [ ] (1 h) Connection status as `role="status"`; retry/offline handling
- [ ] (2 h) Clean `useChat` (dependency arrays, no setTimeout polling; refetch title on event)
- Acceptance: drawer traps focus and closes on Esc; screen reader announces new assistant messages (`aria-live="polite"`); works at 320 px.

### Phase 5 - Reports, Settings, Auth (8 h)
- [ ] (3 h) `ReportsPage` (metric list + 2 charts with token colours, data-table fallbacks, real NumberTicker)
- [ ] (3 h) `SettingsPage` real profile, language, appearance, stage names; remove fake save
- [ ] (2 h) Login/Register restyle, field-level errors, `autocomplete` attributes, show-password button with `aria-label`/`aria-pressed`
- Acceptance: charts readable in both themes (contrast 3:1 for marks), no `hsl(var())` left (`grep`), forms usable with password managers.

### Phase 6 - Tamil pass (8 h)
- [ ] (3 h) Extract all strings to `en.ts` (about 250)
- [ ] (2 h) Draft `ta.ts`, mark `TODO(review)`; Lebi or a native speaker reviews
- [ ] (2 h) Layout stress with `?pseudo=1` (+40 percent length) and real Tamil on every screen at 320/768/1280
- [ ] (1 h) Number/date locale decisions finalised
- Acceptance: zero hard-coded user-facing English strings (ESLint rule or grep check in CI); no truncated Tamil label or clipped glyph in screenshots; `<html lang>` toggles.

### Phase 7 - Quality, performance, docs (10 h)
- [ ] (3 h) vitest unit/component tests (see 8.3)
- [ ] (3 h) Playwright E2E (see 8.4) in Docker (`docker compose run --rm`) per Lebi's convention
- [ ] (2 h) Lighthouse + axe pass and fixes
- [ ] (1 h) `docs-keeper`: update `FRONTEND_DOCUMENTATION.md` (routes, stores, i18n, tokens)
- [ ] (1 h) Rubric showcase page/doc (section 9)
- Acceptance: section 8 fully green.

Stretch (not counted): high-contrast mode, CSV import UI, industry label presets, PWA install + offline shell for the receptionist phone.

---

## 8. Acceptance criteria

### 8.1 Responsive

| Breakpoint (Bootstrap-aligned) | Test width | Must hold |
|---|---|---|
| xs | 320, 375 | No horizontal page scroll; bottom nav; 16 px inputs; 44 px primary targets |
| sm 576 | 600 | Two-column forms allowed |
| md 768 | 768, 820 | Icon rail nav; table appears from here |
| lg 992 | 1024 | Table + side panels |
| xl 1200 | 1280 | Full sidebar |
| xxl 1400 | 1440 | Content capped at 1120 px |

Also: landscape phone (667x375), 200 percent browser zoom (reflow at 320 CSS px, WCAG 1.4.10), 150 percent OS text size.

### 8.2 Lighthouse, a11y, perf (mobile profile, production build served by nginx)

| Metric | Target |
|---|---|
| Lighthouse Performance | >= 90 on Today and Leads (4G throttle, mid-tier CPU) |
| Lighthouse Accessibility | >= 95 on every route; 100 on Login |
| Best Practices / SEO | >= 95 / >= 90 (login page indexable meta only) |
| LCP / INP / CLS | <= 2.5 s / <= 200 ms / <= 0.1 (web.dev "good") |
| Initial JS (gzip) | <= 180 KB; Reports chunk (recharts) lazy-loaded [?: baseline unmeasured] |
| axe-core (via Playwright) | 0 serious/critical violations per route in light, dark, and `ta` |
| Manual a11y | Keyboard-only run of: log in, add lead, mark follow-up done, move a deal, ask assistant; screen-reader spot check (NVDA or Orca) on Today and Pipeline; contrast tokens table re-verified; `prefers-reduced-motion` honoured; touch targets >= 44 px (24 px absolute minimum per WCAG 2.2 SC 2.5.8) |

### 8.3 vitest + Testing Library (add)

- [ ] `format.test.ts`: `formatINR` lakh grouping (1234567 -> Rs 12,34,567), relative dates, plural rules
- [ ] `i18n.test.ts`: every `en` key exists in `ta` (type + runtime), `useT` interpolation, `<html lang>` switch
- [ ] `LanguageToggle.test.tsx`, `ThemeToggle.test.tsx` (persist + `aria-pressed`)
- [ ] `BottomNav.test.tsx` / `SideNav.test.tsx`: active item, labels, `aria-current="page"`
- [ ] `FollowUpRow.test.tsx`: Done, Snooze, Undo, keyboard
- [ ] `LeadsPage.test.tsx`: loading, empty, error+retry, filter URL sync (mock axios)
- [ ] `MoveToMenu.test.tsx` + `useBoardDnd` rollback on failure
- [ ] `ConfirmationCard.test.tsx`: verb labels, dismiss
- [ ] `authStore.test.ts`: login/logout/401 behaviour
- [ ] Coverage: auth store and data-mutation handlers (delete, move stage, create) 100 percent branches (Lebi's rule)

### 8.4 Playwright E2E (add, `e2e/`)

- [ ] `auth.spec.ts`: register, login, bad password message, logout, protected redirect
- [ ] `today.spec.ts`: overdue appears first, mark done, snooze, undo
- [ ] `leads.spec.ts`: create, search, edit, bulk delete with confirm, call link `href="tel:..."`
- [ ] `pipeline.spec.ts`: drag deal (desktop project) and Move-to menu (mobile project)
- [ ] `assistant.spec.ts`: open drawer with `A`, send message (mock/stub backend), confirm card flow
- [ ] `i18n.spec.ts`: toggle to Tamil, `html[lang=ta]`, key labels translated, no horizontal overflow
- [ ] `a11y.spec.ts`: `@axe-core/playwright` on each route x {light, dark} x {en, ta}
- [ ] Projects: Chromium desktop 1440x900, Pixel 5 (393x851), iPhone SE (375x667)
- [ ] Screenshot baselines for Today, Leads, Pipeline, Assistant (en + ta) to catch Tamil overflow regressions

### 8.5 Definition of done per screen

Loading, empty, error and data states exist; works at 320 px; light + dark; en + ta; keyboard operable; axe clean; no hard-coded colours or strings; reduced motion respected; docs updated.

---

## 9. Showcasing HTML5 / CSS3 / Bootstrap / JavaScript / React honestly (rubric)

The app stays React + Tailwind. Do **not** claim Bootstrap is used in the app. These are truthful ways to evidence each rubric item:

| Rubric item | Honest evidence in the repo and report |
|---|---|
| **HTML5** | Semantic landmarks (`header`, `nav aria-label`, `main`, `section`, `article` for timeline items, `time datetime`, `dl` for metrics, `details/summary` for chart tables); form features (`type=email/tel`, `inputmode`, `autocomplete`, `required`, `pattern`, `minlength`, constraint validation messages); `<dialog` semantics via Radix; `lang` attribute switching; `<meta name=theme-color>`; `tel:` and `wa.me` links. Document these in a short table with file references. |
| **CSS3** | Custom properties for the design tokens and theming; Grid + Flexbox layouts; `clamp()` fluid type; media queries incl. `prefers-color-scheme`, `prefers-reduced-motion`; `:lang()` selectors for Tamil metrics; `:focus-visible`; `position: sticky`; `env(safe-area-inset-*)`; `dvh`; transitions; logical properties; container queries for the lead row (optional). Show the `index.css` token block as the "CSS3 centrepiece" in the report. |
| **Bootstrap** | (a) Breakpoints in Tailwind are overridden to Bootstrap 5.3's (576/768/992/1200/1400, getbootstrap.com/docs/5.3/layout/breakpoints) and the same mobile-first `min-width` strategy is used; include a mapping table: `container` -> `max-w` wrapper, `row/col-md-6` -> `grid md:grid-cols-2`, `d-none d-md-block` -> `hidden md:block`, `btn btn-primary` -> shadcn `Button`, `navbar` -> `AppShell`, `modal` -> Radix `Dialog`, `toast` -> sonner, `badge` -> `StatusChip`. This is a concept mapping, stated as such. (b) Optional (2 h): a standalone, clearly-labelled `docs/showcase/bootstrap-parity.html` that loads Bootstrap 5.3 from its CDN and reproduces the Leads list/Today layout, so the marker can see the same grid concepts in real Bootstrap. State in the report that this page is a companion demo and the production UI is Tailwind/shadcn. Ask Lebi / the course staff whether the "Bootstrap" rubric line permits an equivalent framework; if not, option (b) is the honest fallback. |
| **JavaScript / TypeScript** | `strict` TypeScript, discriminated unions for chat WS messages, Zod at API boundaries, custom hooks (`useChat`, `useResource`, `useBoardDnd`), debounced search, optimistic updates with rollback, HTML5 Drag and Drop API plus keyboard alternative, `Intl` APIs (`NumberFormat`, `DateTimeFormat`, `PluralRules`, `RelativeTimeFormat`). |
| **React** | Component tree diagram, lazy routes + Suspense, error boundary, context/Zustand split (server state vs UI state), controlled forms, memoisation where measured. |
| **Front-end design marks (5/30)** | Include in the report: token table, before/after screenshots at 375 and 1440 in light/dark and en/ta, Lighthouse and axe results from section 8, the wireframes above. |

---

## 10. Risks and open questions for Lebi

| # | Item | Default if no answer |
|---|---|---|
| 1 | Backend change for follow-up due dates (Phase 3) is the only non-UI work | Do it; UI falls back to existing `task` activities |
| 2 | Tamil copy review | Lebi reviews; native speaker for client demo |
| 3 | Number digits: Western with lakh grouping vs Tamil digits | Western digits, `en-IN` grouping |
| 4 | Naming "Leads" vs "Patients/Customers" | "Leads"; label presets as stretch |
| 5 | Fontsource availability of `newsreader` and `noto-serif-tamil` packages [?] | Fallback to Inter 600 headings |
| 6 | Bundle baseline unknown (no `node_modules` at audit time) | Measure in Phase 0, then freeze budgets |
| 7 | Framer Motion remains a dependency (stack must not change) but is reduced to sheet/dialog/collapse transitions; could be replaced by CSS later | Keep, lazy |
| 8 | Scope: 75 h is large for a semester deadline | Cut order if short on time: Phase 6 Tamil (keep toggle + 3 key screens), Reports charts, Assistant drawer. Never cut Phase 0-2 |
