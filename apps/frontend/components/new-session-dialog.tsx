"use client";

import { useState, type FormEvent } from "react";
import { useCreateSession } from "@/lib/hooks/use-sessions";
import { useAgents } from "@/lib/hooks/use-agents";
import { usePresets } from "@/lib/hooks/use-presets";
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

interface Props {
  projectId: string;
}

export function NewSessionDialog({ projectId }: Props) {
  const [open, setOpen] = useState(false);
  const [branch, setBranch] = useState("");
  const [commitSha, setCommitSha] = useState("");
  const [diffBaseSha, setDiffBaseSha] = useState("");
  const [agentId, setAgentId] = useState("");
  const [presetId, setPresetId] = useState("");
  const [includePaths, setIncludePaths] = useState("");

  const createSession = useCreateSession(projectId);
  const { data: agents } = useAgents();
  const { data: presets } = usePresets();

  const agentEntries = agents ? Object.entries(agents) : [];

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    await createSession.mutateAsync({
      branch,
      commit_sha: commitSha || null,
      diff_base_sha: diffBaseSha || null,
      preset_id: presetId || "00000000-0000-0000-0000-000000000001",
      agent_id: agentId || "00000000-0000-0000-0000-000000000001",
    });
    setOpen(false);
    setBranch("");
    setCommitSha("");
    setDiffBaseSha("");
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger>
        <Button>분석 실행</Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>새 분석 실행</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="agent">에이전트</Label>
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
            <Label htmlFor="preset">프리셋</Label>
            <Select
              value={presetId}
              onValueChange={(v) => setPresetId(v ?? "")}
            >
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
            <Label htmlFor="branch">브랜치</Label>
            <Input
              id="branch"
              value={branch}
              onChange={(e) => setBranch(e.target.value)}
              placeholder="main, release-1.4, feat/login..."
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label htmlFor="commit">커밋 SHA (선택)</Label>
              <Input
                id="commit"
                value={commitSha}
                onChange={(e) => setCommitSha(e.target.value)}
                placeholder="HEAD"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="diffBase">Diff 기준 SHA (선택)</Label>
              <Input
                id="diffBase"
                value={diffBaseSha}
                onChange={(e) => setDiffBaseSha(e.target.value)}
                placeholder="diff 분석 시 기준점"
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="include">포함 경로 (선택)</Label>
            <Input
              id="include"
              value={includePaths}
              onChange={(e) => setIncludePaths(e.target.value)}
              placeholder="src/api, src/auth (쉼표 구분)"
            />
          </div>

          <Button
            type="submit"
            className="w-full"
            disabled={createSession.isPending}
          >
            {createSession.isPending ? "실행 중..." : "분석 시작"}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
