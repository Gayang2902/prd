"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useCreatePreset } from "@/lib/hooks/use-presets";
import { useAgents } from "@/lib/hooks/use-agents";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export default function NewPresetPage() {
  const router = useRouter();
  const createPreset = useCreatePreset();
  const { data: agents } = useAgents();

  const [name, setName] = useState("");
  const [agentId, setAgentId] = useState("");
  const [versionSha, setVersionSha] = useState("latest");
  const [promptTemplate, setPromptTemplate] = useState("");
  const [ruleset, setRuleset] = useState("{}");
  const [timeoutSeconds, setTimeoutSeconds] = useState("300");
  const [maxRetries, setMaxRetries] = useState("2");
  const [isShared, setIsShared] = useState("false");

  const agentList = agents ?? [];
  const selectedAgentName = agentList.find((a) => a.id === agentId)?.name;

  const handleSubmit = async () => {
    if (!name || !agentId) return;
    let parsedRuleset: Record<string, unknown> = {};
    try {
      parsedRuleset = JSON.parse(ruleset);
    } catch {
      return;
    }
    await createPreset.mutateAsync({
      name,
      agent_id: agentId,
      version_sha: versionSha || "latest",
      prompt_template: promptTemplate || undefined,
      ruleset: parsedRuleset,
      timeout_seconds: parseInt(timeoutSeconds) || 300,
      max_retries: parseInt(maxRetries) || 2,
      is_shared: isShared === "true",
    });
    router.push("/presets");
  };

  return (
    <div className="mx-auto max-w-2xl p-6">
      <Card>
        <CardHeader>
          <CardTitle>새 프리셋</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">이름</Label>
            <Input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="프리셋 이름"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label>에이전트</Label>
              <Select value={agentId} onValueChange={(v) => setAgentId(v ?? "")}>
                <SelectTrigger>
                  <SelectValue placeholder="에이전트 선택">
                    {selectedAgentName}
                  </SelectValue>
                </SelectTrigger>
                <SelectContent>
                  {agentList.map((a) => (
                    <SelectItem key={a.id} value={a.id}>
                      {a.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="version">버전 SHA</Label>
              <Input
                id="version"
                value={versionSha}
                onChange={(e) => setVersionSha(e.target.value)}
                placeholder="latest"
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="prompt">프롬프트 템플릿</Label>
            <textarea
              id="prompt"
              value={promptTemplate}
              onChange={(e) => setPromptTemplate(e.target.value)}
              placeholder="프롬프트 템플릿을 입력하세요..."
              className="flex min-h-[100px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="ruleset">룰셋 (JSON)</Label>
            <textarea
              id="ruleset"
              value={ruleset}
              onChange={(e) => setRuleset(e.target.value)}
              placeholder="{}"
              className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 font-mono text-xs ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div className="space-y-2">
              <Label htmlFor="timeout">타임아웃 (초)</Label>
              <Input
                id="timeout"
                type="number"
                value={timeoutSeconds}
                onChange={(e) => setTimeoutSeconds(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="retries">최대 재시도</Label>
              <Input
                id="retries"
                type="number"
                value={maxRetries}
                onChange={(e) => setMaxRetries(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label>공유</Label>
              <Select value={isShared} onValueChange={(v) => setIsShared(v ?? "false")}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="false">개인</SelectItem>
                  <SelectItem value="true">공유</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {createPreset.error && (
            <p className="text-xs text-[#ff5555]">
              {createPreset.error instanceof Error ? createPreset.error.message : "생성 실패"}
            </p>
          )}

          <div className="flex gap-2">
            <Button
              disabled={createPreset.isPending || !name || !agentId}
              onClick={handleSubmit}
            >
              {createPreset.isPending ? "생성 중..." : "프리셋 생성"}
            </Button>
            <Button variant="outline" onClick={() => router.back()}>
              취소
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
