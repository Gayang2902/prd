import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/lib/api/client", () => ({
  apiFetch: vi.fn(),
}));

import { apiFetch } from "@/lib/api/client";
import {
  fetchSessions,
  fetchSession,
  createSession,
  cancelSession,
  getLogsUrl,
} from "@/lib/api/sessions";

const mockApiFetch = vi.mocked(apiFetch);

beforeEach(() => {
  mockApiFetch.mockReset();
});

describe("sessions API", () => {
  it("fetchSessions", async () => {
    mockApiFetch.mockResolvedValue([]);
    await fetchSessions("p1");
    expect(mockApiFetch).toHaveBeenCalledWith("/projects/p1/sessions");
  });

  it("fetchSession by id", async () => {
    const session = { id: "s1", state: "completed" };
    mockApiFetch.mockResolvedValue(session);
    const result = await fetchSession("s1");
    expect(mockApiFetch).toHaveBeenCalledWith("/sessions/s1");
    expect(result).toEqual(session);
  });

  it("createSession sends POST", async () => {
    const data = { branch: "main", preset_id: "pr1", agent_id: "a1" };
    mockApiFetch.mockResolvedValue({ id: "s2", ...data });
    await createSession("p1", data);
    expect(mockApiFetch).toHaveBeenCalledWith("/projects/p1/sessions", {
      method: "POST",
      body: JSON.stringify(data),
    });
  });

  it("cancelSession sends POST", async () => {
    mockApiFetch.mockResolvedValue({ id: "s1", state: "canceled" });
    await cancelSession("s1");
    expect(mockApiFetch).toHaveBeenCalledWith("/sessions/s1/cancel", {
      method: "POST",
    });
  });

  it("getLogsUrl returns SSE URL", () => {
    const url = getLogsUrl("s1");
    expect(url).toBe("http://localhost:8000/api/v1/sessions/s1/logs");
  });
});
