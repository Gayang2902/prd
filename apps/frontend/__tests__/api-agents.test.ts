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
  it("fetchAgents returns agent registry", async () => {
    const agents = {
      hunting: {
        name: "hunting-agent",
        version: "0.1.0",
        supported_languages: ["python"],
        max_input_size_bytes: 500000,
        cost_profile: { input_per_1k: 0.003 },
        description: "Hunting agent",
      },
    };
    mockApiFetch.mockResolvedValue(agents);
    const result = await fetchAgents();
    expect(mockApiFetch).toHaveBeenCalledWith("/agents");
    expect(result).toEqual(agents);
  });
});
