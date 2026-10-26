import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";
import { server } from "@/test/server";
import { useLocaleStore } from "@/stores/localeStore";
import { TodayPage } from "./TodayPage";

const followUps = [
  {
    id: "f1",
    contact_id: "c1",
    contact_name: "Priya Raman",
    contact_phone: "+919840012345",
    appointment_id: "a1",
    reason: "no_show_recovery",
    due_at: "2020-10-19T04:30:00Z",
    status: "pending",
    draft_en: "Hi Priya, we missed you today. Shall we rebook?",
    draft_ta: null,
    channel: "simulated",
  },
  {
    id: "f2",
    contact_id: "c2",
    contact_name: "Meena Devi",
    contact_phone: null,
    appointment_id: "a2",
    reason: "reminder_24h",
    due_at: "2999-10-27T04:30:00Z",
    status: "pending",
    draft_en: null,
    draft_ta: null,
    channel: "simulated",
  },
];

const summary = {
  appointments: 12,
  no_shows: 3,
  no_show_rate: 0.25,
  pending_tasks: 2,
  messages_sent: 4,
  recovered_inr: 1800,
  recovered_count: 1,
};

function renderToday() {
  return render(
    <MemoryRouter>
      <TodayPage />
    </MemoryRouter>
  );
}

function rowFor(nameElement: HTMLElement): HTMLElement {
  const row = nameElement.closest("li");
  if (!row) throw new Error(`No follow-up row for ${nameElement.textContent}`);
  return row;
}

describe("TodayPage", () => {
  beforeEach(() => {
    useLocaleStore.setState({ locale: "en" });
    server.use(
      http.get("*/api/follow-ups", () => HttpResponse.json(followUps)),
      http.get("*/api/recovery/summary", () => HttpResponse.json(summary))
    );
  });

  it("renders pending follow-ups as ruled rows with the KPI line", async () => {
    renderToday();

    expect(await screen.findByText("Priya Raman")).toBeInTheDocument();
    expect(screen.getByText("Meena Devi")).toBeInTheDocument();
    expect(screen.getByText("Overdue")).toBeInTheDocument();
    expect(rowFor(screen.getByText("Priya Raman")).textContent).toMatch(/Missed appointment · Due .*10:00/);
    expect(screen.getByText("2 pending · 3 no-shows · 25% no-show rate")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "+919840012345" })).toHaveAttribute("href", "tel:+919840012345");
  });

  it("approves a follow-up through the API and removes its row", async () => {
    let approveBody: unknown = null;
    server.use(
      http.post("*/api/follow-ups/f1/approve", async ({ request }) => {
        approveBody = await request.json();
        return HttpResponse.json({
          task: { ...followUps[0], status: "done" },
          message: { id: "m1", language: "en", body: "Hi", status: "sent" },
        });
      })
    );
    renderToday();

    const row = rowFor(await screen.findByText("Priya Raman"));
    fireEvent.click(within(row).getByRole("button", { name: "Approve" }));

    await waitFor(() => expect(screen.queryByText("Priya Raman")).not.toBeInTheDocument());
    expect(approveBody).toEqual({ language: "en" });
    expect(screen.getByText("Meena Devi")).toBeInTheDocument();
  });

  it("skips a follow-up through the API and removes its row", async () => {
    let skipped = false;
    server.use(
      http.post("*/api/follow-ups/f2/skip", () => {
        skipped = true;
        return HttpResponse.json({ ...followUps[1], status: "skipped" });
      })
    );
    renderToday();

    const row = rowFor(await screen.findByText("Meena Devi"));
    fireEvent.click(within(row).getByRole("button", { name: "Skip" }));

    await waitFor(() => expect(screen.queryByText("Meena Devi")).not.toBeInTheDocument());
    expect(skipped).toBe(true);
  });

  it("shows the empty state when nothing is due", async () => {
    server.use(http.get("*/api/follow-ups", () => HttpResponse.json([])));
    renderToday();

    expect(await screen.findByRole("heading", { name: "Nothing due right now" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open appointments" })).toHaveAttribute("href", "/appointments");
  });

  it("shows a retry banner instead of an empty list when loading fails", async () => {
    server.use(http.get("*/api/follow-ups", () => HttpResponse.json({ detail: "Down" }, { status: 500 })));
    renderToday();

    expect(await screen.findByRole("alert")).toHaveTextContent("This could not be loaded.");
    expect(screen.queryByRole("heading", { name: "Nothing due right now" })).not.toBeInTheDocument();
  });
});
