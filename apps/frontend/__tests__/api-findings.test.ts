import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/lib/api/client", () => ({
  apiFetch: vi.fn(),
}));

import { apiFetch } from "@/lib/api/client";
import {
  fetchFindings,
  updateFindingStatus,
  fetchFindingTimeline,
} from "@/lib/api/findings";

const mockApiFetch = vi.mocked(apiFetch);

beforeEach(() => {
  mockApiFetch.mockReset();
});

describe("findings API", () => {
  it("fetchFindings without params", async () => {
    mockApiFetch.mockResolvedValue([]);
    await fetchFindings("s1");
    expect(mockApiFetch).toHaveBeenCalledWith("/sessions/s1/findings");
  });

  it("fetchFindings with severity filter", async () => {
    mockApiFetch.mockResolvedValue([]);
    await fetchFindings("s1", { severity: "critical" });
    expect(mockApiFetch).toHaveBeenCalledWith(
      "/sessions/s1/findings?severity=critical",
    );
  });

  it("updateFindingStatus sends PATCH", async () => {
    const data = { status: "confirmed", reason: "verified" };
    mockApiFetch.mockResolvedValue({ id: "fs1", ...data });
    await updateFindingStatus("f1", data);
    expect(mockApiFetch).toHaveBeenCalledWith("/findings/f1/status", {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  });

  it("fetchFindingTimeline", async () => {
    mockApiFetch.mockResolvedValue([{ id: "fs1" }]);
    const result = await fetchFindingTimeline("f1");
    expect(mockApiFetch).toHaveBeenCalledWith("/findings/f1/timeline");
    expect(result).toHaveLength(1);
  });
});
