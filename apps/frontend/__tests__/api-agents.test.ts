import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/lib/api/client", () => ({
  apiFetch: vi.fn(),
}));

import { apiFetch } from "@/lib/api/client";
import { fetchAgents } from "@/lib/api/agents";

const mockApiFetch = vi.mocked(apiFetch);

beforeEach(() => {
  mockApiFetch.mockReset();
});

describe("agents API", () => {
  it("fetchAgents returns agent list", async () => {
    const agents = [
      {
        id: "00000000-0000-0000-0000-000000000011",
        name: "hunting-agent",
        version: "1.0.0",
        description: "Hunting agent",
      },
    ];
    mockApiFetch.mockResolvedValue(agents);
    const result = await fetchAgents();
    expect(mockApiFetch).toHaveBeenCalledWith("/agents");
    expect(result).toEqual(agents);
  });
});
