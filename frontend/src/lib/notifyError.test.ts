import { beforeEach, describe, expect, it, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { toast } from "sonner";
import client from "@/api/client";
import { server } from "@/test/server";
import { useLocaleStore } from "@/stores/localeStore";
import { notifyApiError } from "./notifyError";

vi.mock("sonner", () => ({
  toast: { error: vi.fn(), success: vi.fn() },
}));

describe("notifyApiError", () => {
  beforeEach(() => {
    vi.mocked(toast.error).mockClear();
    useLocaleStore.setState({ locale: "en" });
  });

  it("shows the fallback title and the server detail for a failed API call", async () => {
    server.use(http.get("*/api/appointments", () => HttpResponse.json({ detail: "Slot already booked" }, { status: 409 })));

    const error: unknown = await client.get("/appointments").catch((reason: unknown) => reason);
    notifyApiError(error);

    expect(toast.error).toHaveBeenCalledWith("Something went wrong. Please try again.", {
      description: "Slot already booked",
    });
  });

  it("omits the description when the server detail is not plain text", async () => {
    server.use(
      http.get("*/api/appointments", () =>
        HttpResponse.json({ detail: [{ msg: "field required" }] }, { status: 422 })
      )
    );

    const error: unknown = await client.get("/appointments").catch((reason: unknown) => reason);
    notifyApiError(error);

    expect(toast.error).toHaveBeenCalledWith("Something went wrong. Please try again.", {
      description: undefined,
    });
  });

  it("uses the Tamil fallback when the locale is Tamil", () => {
    useLocaleStore.setState({ locale: "ta" });

    notifyApiError(new Error("network down"));

    expect(toast.error).toHaveBeenCalledWith("ஏதோ தவறு நடந்தது. மீண்டும் முயற்சிக்கவும்.", {
      description: undefined,
    });
  });
});
