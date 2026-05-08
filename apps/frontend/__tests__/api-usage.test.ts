import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/lib/api/client", () => ({
  apiFetch: vi.fn(),
}));

import { apiFetch } from "@/lib/api/client";
import {
  fetchCostSummary,
  fetchCostByProject,
  fetchCostByAgent,
  fetchDailyCost,
} from "@/lib/api/usage";
import { fetchAuditLogs } from "@/lib/api/audit";
import { fetchRegressionHistory } from "@/lib/api/regression";
import { fetchAgents } from "@/lib/api/agents";

const mockApiFetch = vi.mocked(apiFetch);

beforeEach(() => {
  mockApiFetch.mockReset();
});

describe("usage API", () => {
  it("fetchCostSummary without dates", async () => {
    mockApiFetch.mockResolvedValue({ total_sessions: 10 });
    await fetchCostSummary();
    expect(mockApiFetch).toHaveBeenCalledWith("/usage/cost");
  });

  it("fetchCostSummary with date range", async () => {
    mockApiFetch.mockResolvedValue({});
    await fetchCostSummary("2025-01-01", "2025-01-31");
    expect(mockApiFetch).toHaveBeenCalledWith(
      "/usage/cost?since=2025-01-01&until=2025-01-31",
    );
  });

  it("fetchCostByProject", async () => {
    mockApiFetch.mockResolvedValue([]);
    await fetchCostByProject("2025-01-01");
    expect(mockApiFetch).toHaveBeenCalledWith(
      "/usage/by-project?since=2025-01-01",
    );
  });

  it("fetchCostByAgent", async () => {
    mockApiFetch.mockResolvedValue([]);
    await fetchCostByAgent();
    expect(mockApiFetch).toHaveBeenCalledWith("/usage/by-agent");
  });

  it("fetchDailyCost", async () => {
    mockApiFetch.mockResolvedValue([]);
    await fetchDailyCost(undefined, "2025-12-31");
    expect(mockApiFetch).toHaveBeenCalledWith("/usage/daily?until=2025-12-31");
  });
});

describe("audit API", () => {
  it("fetchAuditLogs without params", async () => {
    mockApiFetch.mockResolvedValue([]);
    await fetchAuditLogs();
    expect(mockApiFetch).toHaveBeenCalledWith("/audit/logs");
  });

  it("fetchAuditLogs with filters", async () => {
    mockApiFetch.mockResolvedValue([]);
    await fetchAuditLogs({ action: "login", limit: 50, offset: 10 });
    expect(mockApiFetch).toHaveBeenCalledWith(
      "/audit/logs?action=login&limit=50&offset=10",
    );
  });

  it("fetchAuditLogs with resource_type", async () => {
    mockApiFetch.mockResolvedValue([]);
    await fetchAuditLogs({ resource_type: "project" });
    expect(mockApiFetch).toHaveBeenCalledWith(
      "/audit/logs?resource_type=project",
    );
  });
});

describe("regression API", () => {
  it("fetchRegressionHistory", async () => {
    mockApiFetch.mockResolvedValue([{ session_id: "s1", new: 3 }]);
    const result = await fetchRegressionHistory("p1");
    expect(mockApiFetch).toHaveBeenCalledWith(
      "/projects/p1/regression-history",
    );
    expect(result).toHaveLength(1);
  });
});

describe("agents API", () => {
  it("fetchAgents", async () => {
    const agents = [{ id: "uuid-1", name: "mock", version: "1.0", description: "" }];
    mockApiFetch.mockResolvedValue(agents);
    const result = await fetchAgents();
    expect(mockApiFetch).toHaveBeenCalledWith("/agents");
    expect(result).toEqual(agents);
  });
});
