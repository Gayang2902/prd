"use client";

import { useState, type FormEvent } from "react";
import {
  useCreateTargetDiscovery,
  useCreateZeroDayHunt,
} from "@/lib/hooks/use-hunting";
import { useAgents } from "@/lib/hooks/use-agents";
import { usePresets } from "@/lib/hooks/use-presets";
import { useProjects } from "@/lib/hooks/use-projects";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

type HuntingType = "target_discovery" | "zero_day_hunting";

export function NewHuntingDialog() {
  const [open, setOpen] = useState(false);
  const [huntingType, setHuntingType] = useState<HuntingType>("target_discovery");
  const [projectId, setProjectId] = useState("");
  const [agentId, setAgentId] = useState("");
  const [presetId, setPresetId] = useState("");
  const [commitSha, setCommitSha] = useState("");

  const createTarget = useCreateTargetDiscovery();
  const createZeroDay = useCreateZeroDayHunt();
  const { data: projects } = useProjects();
  const { data: agents } = useAgents();
  const { data: presets } = usePresets();

  const agentEntries = agents ? Object.entries(agents) : [];
  const isPending = createTarget.isPending || createZeroDay.isPending;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const payload = {
      project_id: projectId,
      preset_id: presetId || "00000000-0000-0000-0000-000000000001",
      agent_id: agentId || "00000000-0000-0000-0000-000000000001",
      commit_sha: commitSha || null,
    };

    if (huntingType === "target_discovery") {
      await createTarget.mutateAsync(payload);
    } else {
      await createZeroDay.mutateAsync(payload);
    }

    setOpen(false);
    setCommitSha("");
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger>
        <Button>새 헌팅 세션</Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>헌팅 세션 생성</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label>유형</Label>
            <Select
              value={huntingType}
              onValueChange={(v) => setHuntingType(v as HuntingType)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="target_discovery">
                  타겟 디스커버리
                </SelectItem>
                <SelectItem value="zero_day_hunting">
                  제로데이 헌팅
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label>프로젝트</Label>
            <Select value={projectId} onValueChange={(v) => setProjectId(v ?? "")}>
              <SelectTrigger>
                <SelectValue placeholder="프로젝트 선택" />
              </SelectTrigger>
              <SelectContent>
                {(projects ?? []).map((p) => (
                  <SelectItem key={p.id} value={p.id}>
                    {p.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label>에이전트</Label>
            <Select value={agentId} onValueChange={(v) => setAgentId(v ?? "")}>
              <SelectTrigger>
                <SelectValue placeholder="에이전트 선택" />
              </SelectTrigger>
              <SelectContent>
                {agentEntries.map(([name, info]) => (
                  <SelectItem key={name} value={name}>
                    {name} — {info.description.slice(0, 50)}
                  </SelectItem>
                ))}
                {agentEntries.length === 0 && (
                  <SelectItem value="mock">mock (기본)</SelectItem>
                )}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label>프리셋</Label>
            <Select value={presetId} onValueChange={(v) => setPresetId(v ?? "")}>
              <SelectTrigger>
                <SelectValue placeholder="프리셋 선택" />
              </SelectTrigger>
              <SelectContent>
                {(presets ?? []).map((p) => (
                  <SelectItem key={p.id} value={p.id}>
                    {p.name}
                  </SelectItem>
                ))}
                {(!presets || presets.length === 0) && (
                  <SelectItem value="00000000-0000-0000-0000-000000000001">
                    기본 프리셋
                  </SelectItem>
                )}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label>커밋 SHA (선택)</Label>
            <Input
              value={commitSha}
              onChange={(e) => setCommitSha(e.target.value)}
              placeholder="HEAD"
            />
          </div>

          <div className="rounded-md border border-[#6272a4] p-3 text-xs text-muted-foreground">
            {huntingType === "target_discovery" ? (
              <p>
                6단계 파이프라인: 수집 → 필터링 → 스코어링 → 숏리스트 → 완료.
                Centralized MAS로 병렬 수집 후 SAS 판단.
              </p>
            ) : (
              <p>
                7단계 파이프라인: 셋업 → 퍼징 → 트리아지 → 코드 리딩 → 우회 →
                교차 검증 → 완료. Hybrid MAS/SAS 아키텍처.
              </p>
            )}
          </div>

          <Button type="submit" className="w-full" disabled={isPending || !projectId}>
            {isPending ? "생성 중..." : "헌팅 시작"}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
