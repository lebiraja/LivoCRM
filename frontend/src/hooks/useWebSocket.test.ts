import { renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse, type JsonBodyType } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { server } from "@/test/server";
import { useWebSocket } from "./useWebSocket";

const JWT = "header.payload.signature";

/** Minimal WebSocket stand-in that records construction order. */
class FakeWebSocket {
  static instances: FakeWebSocket[] = [];
  url: string;
  onopen: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  close = vi.fn();

  constructor(url: string) {
    this.url = url;
    events.push(`connect ${url}`);
    FakeWebSocket.instances.push(this);
  }
}

let events: string[] = [];
let ticketBodies: unknown[] = [];
let ticketAuthHeaders: (string | null)[] = [];

function mockTicketEndpoint(responses: JsonBodyType[]) {
  let call = 0;
  server.use(
    http.post("*/api/ws/ticket", async ({ request }) => {
      events.push("ticket");
      ticketBodies.push(await request.json());
      ticketAuthHeaders.push(request.headers.get("Authorization"));
      return HttpResponse.json(responses[Math.min(call++, responses.length - 1)]);
    })
  );
}

beforeEach(() => {
  events = [];
  ticketBodies = [];
  ticketAuthHeaders = [];
  FakeWebSocket.instances = [];
  vi.stubGlobal("WebSocket", FakeWebSocket);
  localStorage.setItem("access_token", JWT);
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("useWebSocket", () => {
  it("requests a ticket before connecting and keeps the JWT out of the URL", async () => {
    mockTicketEndpoint([{ ticket: "t-1", expires_in: 30 }]);

    renderHook(() => useWebSocket({ channel: "chat", id: "sess-1" }));

    await waitFor(() => expect(FakeWebSocket.instances).toHaveLength(1));
    expect(events).toEqual(["ticket", "connect ws://localhost:3000/ws/chat/sess-1?ticket=t-1"]);
    expect(ticketBodies).toEqual([{ channel: "chat", session_id: "sess-1" }]);
    expect(ticketAuthHeaders).toEqual([`Bearer ${JWT}`]);
    expect(FakeWebSocket.instances[0].url).not.toContain(JWT);
    expect(FakeWebSocket.instances[0].url).not.toContain("token=");
  });

  it("sends the dashboard channel body and connects to the user path", async () => {
    mockTicketEndpoint([{ ticket: "t-d", expires_in: 30 }]);

    renderHook(() => useWebSocket({ channel: "dashboard", id: "user-1" }));

    await waitFor(() => expect(FakeWebSocket.instances).toHaveLength(1));
    expect(ticketBodies).toEqual([{ channel: "dashboard" }]);
    expect(FakeWebSocket.instances[0].url).toBe("ws://localhost:3000/ws/dashboard/user-1?ticket=t-d");
  });

  it("fetches a fresh ticket on every reconnect", async () => {
    mockTicketEndpoint([
      { ticket: "t-1", expires_in: 30 },
      { ticket: "t-2", expires_in: 30 },
    ]);
    const onStatus = vi.fn();

    renderHook(() => useWebSocket({ channel: "chat", id: "sess-1", onStatus }));
    await waitFor(() => expect(FakeWebSocket.instances).toHaveLength(1));
    FakeWebSocket.instances[0].onopen?.();
    expect(onStatus).toHaveBeenLastCalledWith("connected");

    FakeWebSocket.instances[0].onclose?.();
    expect(onStatus).toHaveBeenLastCalledWith("disconnected");

    await waitFor(() => expect(FakeWebSocket.instances).toHaveLength(2), { timeout: 3000 });
    expect(events).toEqual([
      "ticket",
      "connect ws://localhost:3000/ws/chat/sess-1?ticket=t-1",
      "ticket",
      "connect ws://localhost:3000/ws/chat/sess-1?ticket=t-2",
    ]);
  });

  it("does not reconnect after unmount", async () => {
    mockTicketEndpoint([{ ticket: "t-1", expires_in: 30 }]);
    const onStatus = vi.fn();

    const { unmount } = renderHook(() => useWebSocket({ channel: "chat", id: "sess-1", onStatus }));
    await waitFor(() => expect(FakeWebSocket.instances).toHaveLength(1));
    const socket = FakeWebSocket.instances[0];

    vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
    unmount();
    // Browsers fire onclose after close(); that must not schedule a retry
    socket.onclose?.();
    vi.advanceTimersByTime(60_000);

    expect(socket.close).toHaveBeenCalledOnce();
    expect(onStatus.mock.calls.filter(([s]) => s === "connecting")).toHaveLength(1);
  });

  it("does not connect when the ticket response is malformed", async () => {
    mockTicketEndpoint([{ token: JWT }]);
    const onStatus = vi.fn();

    renderHook(() => useWebSocket({ channel: "chat", id: "sess-1", onStatus }));

    await waitFor(() => expect(onStatus).toHaveBeenLastCalledWith("disconnected"));
    expect(FakeWebSocket.instances).toHaveLength(0);
  });

  it("stays disconnected without an id", () => {
    mockTicketEndpoint([{ ticket: "t-1", expires_in: 30 }]);

    renderHook(() => useWebSocket({ channel: "chat", id: null }));

    expect(events).toEqual([]);
  });
});
