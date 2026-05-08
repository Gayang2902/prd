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
import { cn } from "@/lib/utils";

type HuntingType = "target_discovery" | "zero_day_hunting";
type Step = "select" | "configure";

function TargetIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="24" cy="24" r="20" stroke="currentColor" strokeWidth="2" />
      <circle cx="24" cy="24" r="14" stroke="currentColor" strokeWidth="2" />
      <circle cx="24" cy="24" r="8" stroke="currentColor" strokeWidth="2" />
      <circle cx="24" cy="24" r="3" fill="currentColor" />
      <line x1="24" y1="0" x2="24" y2="8" stroke="currentColor" strokeWidth="2" />
      <line x1="24" y1="40" x2="24" y2="48" stroke="currentColor" strokeWidth="2" />
      <line x1="0" y1="24" x2="8" y2="24" stroke="currentColor" strokeWidth="2" />
      <line x1="40" y1="24" x2="48" y2="24" stroke="currentColor" strokeWidth="2" />
    </svg>
  );
}

function BugIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
      <ellipse cx="24" cy="28" rx="10" ry="12" stroke="currentColor" strokeWidth="2" />
      <circle cx="24" cy="14" r="6" stroke="currentColor" strokeWidth="2" />
      <line x1="14" y1="24" x2="6" y2="20" stroke="currentColor" strokeWidth="2" />
      <line x1="34" y1="24" x2="42" y2="20" stroke="currentColor" strokeWidth="2" />
      <line x1="14" y1="30" x2="4" y2="32" stroke="currentColor" strokeWidth="2" />
      <line x1="34" y1="30" x2="44" y2="32" stroke="currentColor" strokeWidth="2" />
      <line x1="14" y1="36" x2="8" y2="42" stroke="currentColor" strokeWidth="2" />
      <line x1="34" y1="36" x2="40" y2="42" stroke="currentColor" strokeWidth="2" />
      <line x1="20" y1="8" x2="16" y2="2" stroke="currentColor" strokeWidth="2" />
      <line x1="28" y1="8" x2="32" y2="2" stroke="currentColor" strokeWidth="2" />
    </svg>
  );
}

export function NewHuntingDialog() {
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState<Step>("select");
  const [huntingType, setHuntingType] = useState<HuntingType>("target_discovery");
  const [projectId, setProjectId] = useState("");
  const [agentId, setAgentId] = useState("");
  const [presetId, setPresetId] = useState("");
  const [commitSha, setCommitSha] = useState("");
  const [keyword, setKeyword] = useState("");
  const [ecosystem, setEcosystem] = useState("");
  const [targetRepo, setTargetRepo] = useState("");
  const [fuzzingWorkers, setFuzzingWorkers] = useState("3");

  const createTarget = useCreateTargetDiscovery();
  const createZeroDay = useCreateZeroDayHunt();
  const { data: projects } = useProjects();
  const { data: agents } = useAgents();
  const { data: presets } = usePresets();

  const agentEntries = agents ? Object.entries(agents) : [];
  const isPending = createTarget.isPending || createZeroDay.isPending;

  const reset = () => {
    setStep("select");
    setCommitSha("");
    setKeyword("");
    setEcosystem("");
    setTargetRepo("");
    setFuzzingWorkers("3");
  };

  const handleSelect = (type: HuntingType) => {
    setHuntingType(type);
    setStep("configure");
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const config: Record<string, unknown> = {
      skill: huntingType === "target_discovery" ? "opentarget" : "openresearch",
      session_type: huntingType,
    };
    if (huntingType === "target_discovery") {
      if (keyword) config.keyword = keyword;
      if (ecosystem) config.ecosystem = ecosystem;
    } else {
      if (targetRepo) config.target_repo = targetRepo;
      config.fuzzing_workers = parseInt(fuzzingWorkers) || 3;
    }

    const payload = {
      project_id: projectId,
      preset_id: presetId || "00000000-0000-0000-0000-000000000001",
      agent_id: agentId || "00000000-0000-0000-0000-000000000010",
      commit_sha: commitSha || null,
      config,
    };

    if (huntingType === "target_discovery") {
      await createTarget.mutateAsync(payload);
    } else {
      await createZeroDay.mutateAsync(payload);
    }

    setOpen(false);
    reset();
  };

  return (
    <Dialog open={open} onOpenChange={(v) => { setOpen(v); if (!v) reset(); }}>
      <DialogTrigger>
        <Button>새 헌팅 세션</Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>
            {step === "select" ? "헌팅 유형 선택" : (
              huntingType === "target_discovery" ? "타겟 디스커버리 설정" : "제로데이 헌팅 설정"
            )}
          </DialogTitle>
        </DialogHeader>

        {step === "select" ? (
          <div className="grid grid-cols-2 gap-4 py-4">
            <button
              type="button"
              onClick={() => handleSelect("target_discovery")}
              className={cn(
                "flex flex-col items-center gap-4 rounded-xl border-2 border-[#44475a] p-6",
                "transition-all hover:border-[#8be9fd] hover:bg-[#8be9fd]/10",
                "focus:outline-none focus:ring-2 focus:ring-[#8be9fd]",
              )}
            >
              <TargetIcon className="h-16 w-16 text-[#8be9fd]" />
              <div className="text-center">
                <p className="text-base font-bold text-[#f8f8f2]">타겟 디스커버리</p>
                <p className="mt-1 text-xs text-[#6272a4] leading-relaxed">
                  깨지기 쉬운 오픈소스 타겟을<br />병렬 수집으로 빠르게 탐색
                </p>
              </div>
              <div className="flex flex-wrap justify-center gap-1">
                {["수집", "필터링", "스코어링", "숏리스트"].map((p) => (
                  <span key={p} className="rounded bg-[#44475a] px-1.5 py-0.5 text-[10px] text-[#8be9fd]">
                    {p}
                  </span>
                ))}
              </div>
            </button>

            <button
              type="button"
              onClick={() => handleSelect("zero_day_hunting")}
              className={cn(
                "flex flex-col items-center gap-4 rounded-xl border-2 border-[#44475a] p-6",
                "transition-all hover:border-[#ff5555] hover:bg-[#ff5555]/10",
                "focus:outline-none focus:ring-2 focus:ring-[#ff5555]",
              )}
            >
              <BugIcon className="h-16 w-16 text-[#ff5555]" />
              <div className="text-center">
                <p className="text-base font-bold text-[#f8f8f2]">제로데이 헌팅</p>
                <p className="mt-1 text-xs text-[#6272a4] leading-relaxed">
                  Hybrid MAS/SAS 아키텍처로<br />제로데이 취약점 탐색 및 검증
                </p>
              </div>
              <div className="flex flex-wrap justify-center gap-1">
                {["퍼징", "트리아지", "코드리딩", "우회", "검증"].map((p) => (
                  <span key={p} className="rounded bg-[#44475a] px-1.5 py-0.5 text-[10px] text-[#ff5555]">
                    {p}
                  </span>
                ))}
              </div>
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="text-xs text-muted-foreground"
              onClick={() => setStep("select")}
            >
              &larr; 유형 다시 선택
            </Button>

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

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label>에이전트</Label>
                <Select value={agentId} onValueChange={(v) => setAgentId(v ?? "")}>
                  <SelectTrigger>
                    <SelectValue placeholder="에이전트 선택" />
                  </SelectTrigger>
                  <SelectContent>
                    {agentEntries.map(([name, info]) => (
                      <SelectItem key={name} value={name}>
                        {name}
                      </SelectItem>
                    ))}
                    {agentEntries.length === 0 && (
                      <SelectItem value="mock">기본 에이전트</SelectItem>
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
            </div>

            <div className="space-y-2">
              <Label>커밋 SHA (선택)</Label>
              <Input
                value={commitSha}
                onChange={(e) => setCommitSha(e.target.value)}
                placeholder="HEAD"
              />
            </div>

            {huntingType === "target_discovery" ? (
              <div className="space-y-3 rounded-lg border border-[#8be9fd]/30 bg-[#8be9fd]/5 p-4">
                <p className="text-xs font-semibold text-[#8be9fd]">타겟 디스커버리 설정</p>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <Label className="text-xs">키워드</Label>
                    <Input
                      value={keyword}
                      onChange={(e) => setKeyword(e.target.value)}
                      placeholder="parser, native addon..."
                      className="h-8 text-xs"
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">에코시스템</Label>
                    <Select value={ecosystem} onValueChange={(v) => setEcosystem(v ?? "")}>
                      <SelectTrigger className="h-8 text-xs">
                        <SelectValue placeholder="전체" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="npm">npm</SelectItem>
                        <SelectItem value="pypi">PyPI</SelectItem>
                        <SelectItem value="crates">crates.io</SelectItem>
                        <SelectItem value="go">Go</SelectItem>
                        <SelectItem value="maven">Maven</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <p className="text-[10px] text-[#6272a4]">
                  Centralized MAS (3 agents) 병렬 수집 → SAS 필터링/점수화 → 최종 숏리스트
                </p>
              </div>
            ) : (
              <div className="space-y-3 rounded-lg border border-[#ff5555]/30 bg-[#ff5555]/5 p-4">
                <p className="text-xs font-semibold text-[#ff5555]">제로데이 헌팅 설정</p>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <Label className="text-xs">타겟 저장소 URL</Label>
                    <Input
                      value={targetRepo}
                      onChange={(e) => setTargetRepo(e.target.value)}
                      placeholder="https://github.com/org/repo"
                      className="h-8 text-xs"
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">퍼징 Worker 수</Label>
                    <Select value={fuzzingWorkers} onValueChange={(v) => setFuzzingWorkers(v ?? "3")}>
                      <SelectTrigger className="h-8 text-xs">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="1">1</SelectItem>
                        <SelectItem value="2">2</SelectItem>
                        <SelectItem value="3">3 (권장)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <p className="text-[10px] text-[#6272a4]">
                  병렬 퍼징 → SAS 트리아지 → Opus 코드 리딩 → 병렬 Bypass → CCG 교차 검증
                </p>
              </div>
            )}

            <Button
              type="submit"
              className={cn(
                "w-full",
                huntingType === "target_discovery"
                  ? "bg-[#8be9fd] text-[#282a36] hover:bg-[#8be9fd]/80"
                  : "bg-[#ff5555] text-[#282a36] hover:bg-[#ff5555]/80",
              )}
              disabled={isPending || !projectId}
            >
              {isPending ? "생성 중..." : (
                huntingType === "target_discovery" ? "타겟 디스커버리 시작" : "제로데이 헌팅 시작"
              )}
            </Button>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
