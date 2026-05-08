import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/lib/api/client", () => ({
  apiFetch: vi.fn(),
}));

import { apiFetch } from "@/lib/api/client";
import {
  createTargetDiscovery,
  createZeroDayHunt,
  updatePhase,
  fetchTargetCandidates,
} from "@/lib/api/hunting";

const mockApiFetch = vi.mocked(apiFetch);

beforeEach(() => {
  mockApiFetch.mockReset();
});

describe("hunting API", () => {
  const basePayload = {
    project_id: "p1",
    preset_id: "pr1",
    agent_id: "a1",
    config: { skill: "opentarget" },
  };

  it("createTargetDiscovery sends POST to /hunting/target-discovery", async () => {
    mockApiFetch.mockResolvedValue({ id: "s1", ...basePayload });
    await createTargetDiscovery(basePayload);
    expect(mockApiFetch).toHaveBeenCalledWith("/hunting/target-discovery", {
      method: "POST",
      body: JSON.stringify(basePayload),
    });
  });

  it("createZeroDayHunt sends POST to /hunting/zero-day", async () => {
    const payload = { ...basePayload, config: { skill: "openresearch" } };
    mockApiFetch.mockResolvedValue({ id: "s2", ...payload });
    await createZeroDayHunt(payload);
    expect(mockApiFetch).toHaveBeenCalledWith("/hunting/zero-day", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  });

  it("updatePhase sends PATCH with phase data", async () => {
    const phaseData = { phase: "fuzzing", status: "running", data: { progress: 50 } };
    mockApiFetch.mockResolvedValue({ id: "s1", current_phase: "fuzzing" });
    await updatePhase("s1", phaseData);
    expect(mockApiFetch).toHaveBeenCalledWith("/hunting/sessions/s1/phase", {
      method: "PATCH",
      body: JSON.stringify(phaseData),
    });
  });

  it("fetchTargetCandidates fetches GET /hunting/sessions/:id/targets", async () => {
    const candidates = [{ id: "f1", title: "target-lib", severity: "high" }];
    mockApiFetch.mockResolvedValue(candidates);
    const result = await fetchTargetCandidates("s1");
    expect(mockApiFetch).toHaveBeenCalledWith("/hunting/sessions/s1/targets");
    expect(result).toEqual(candidates);
  });
});
