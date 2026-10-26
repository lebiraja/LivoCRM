import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";
import { server } from "@/test/server";
import { useLocaleStore } from "@/stores/localeStore";
import { AppointmentsPage } from "./AppointmentsPage";

const bookedAppointment = {
  id: "a1",
  contact_id: "c1",
  contact_name: "Karthik S",
  starts_at: "2020-10-20T10:30:00Z",
  fee_inr: "1200.00",
  status: "booked",
  notes: null,
};

const contacts = {
  total: 1,
  items: [
    {
      id: "c2",
      name: "Meena Devi",
      email: null,
      phone: null,
      company: null,
      tags: [],
      notes: null,
      lead_score: null,
      created_at: "2026-10-01T00:00:00Z",
      updated_at: "2026-10-01T00:00:00Z",
    },
  ],
};

function renderAppointments() {
  return render(
    <MemoryRouter>
      <AppointmentsPage />
    </MemoryRouter>
  );
}

describe("AppointmentsPage", () => {
  beforeEach(() => {
    useLocaleStore.setState({ locale: "en" });
  });

  it("creates an appointment, sending the IST time as UTC", async () => {
    let posted: unknown = null;
    server.use(
      http.get("*/api/appointments", () => HttpResponse.json([])),
      http.get("*/api/contacts/", () => HttpResponse.json(contacts)),
      http.post("*/api/appointments", async ({ request }) => {
        posted = await request.json();
        return HttpResponse.json(
          {
            id: "a2",
            contact_id: "c2",
            contact_name: "Meena Devi",
            starts_at: "2026-10-27T04:30:00Z",
            fee_inr: "1200.00",
            status: "booked",
            notes: "Cleaning",
          },
          { status: 201 }
        );
      })
    );
    renderAppointments();

    fireEvent.click(await screen.findByRole("button", { name: "New appointment" }));
    const contactSelect = await screen.findByLabelText("Contact");
    await screen.findByRole("option", { name: "Meena Devi" });
    fireEvent.change(contactSelect, { target: { value: "c2" } });
    fireEvent.change(screen.getByLabelText("Date and time (IST)"), { target: { value: "2026-10-27T10:00" } });
    fireEvent.change(screen.getByLabelText("Fee (₹)"), { target: { value: "1200" } });
    fireEvent.change(screen.getByLabelText("Notes"), { target: { value: "Cleaning" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    expect(await screen.findByText("Meena Devi")).toBeInTheDocument();
    expect(posted).toEqual({
      contact_id: "c2",
      starts_at: "2026-10-27T04:30:00.000Z",
      fee_inr: 1200,
      notes: "Cleaning",
    });
  });

  it("blocks submit and shows field errors when the fee is missing", async () => {
    let posted = false;
    server.use(
      http.get("*/api/appointments", () => HttpResponse.json([])),
      http.get("*/api/contacts/", () => HttpResponse.json(contacts)),
      http.post("*/api/appointments", () => {
        posted = true;
        return HttpResponse.json({}, { status: 500 });
      })
    );
    renderAppointments();

    fireEvent.click(await screen.findByRole("button", { name: "New appointment" }));
    await screen.findByRole("option", { name: "Meena Devi" });
    fireEvent.change(screen.getByLabelText("Contact"), { target: { value: "c2" } });
    fireEvent.change(screen.getByLabelText("Date and time (IST)"), { target: { value: "2026-10-27T10:00" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    expect(await screen.findByText("Enter a fee of ₹0 or more.")).toBeInTheDocument();
    expect(screen.getByLabelText("Fee (₹)")).toHaveAttribute("aria-invalid", "true");
    expect(posted).toBe(false);
  });

  it("marks a booked appointment as no-show", async () => {
    let patched: unknown = null;
    server.use(
      http.get("*/api/appointments", () => HttpResponse.json([bookedAppointment])),
      http.patch("*/api/appointments/a1", async ({ request }) => {
        patched = await request.json();
        return HttpResponse.json({ ...bookedAppointment, status: "no_show" });
      })
    );
    renderAppointments();

    fireEvent.click(await screen.findByRole("button", { name: "Mark no-show" }));

    await waitFor(() => expect(screen.getByText("No-show")).toBeInTheDocument());
    expect(patched).toEqual({ status: "no_show" });
    expect(screen.queryByRole("button", { name: "Mark no-show" })).not.toBeInTheDocument();
  });
});
