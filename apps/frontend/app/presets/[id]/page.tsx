"use client";

import { use, useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { fetchPreset } from "@/lib/api/presets";
import { useUpdatePreset, useDeletePreset } from "@/lib/hooks/use-presets";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export default function PresetDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const router = useRouter();
  const { data: preset, isLoading, error } = useQuery({
    queryKey: ["preset", id],
    queryFn: () => fetchPreset(id),
  });

  const updatePreset = useUpdatePreset();
  const deletePreset = useDeletePreset();

  const [editing, setEditing] = useState(false);
  const [name, setName] = useState("");
  const [promptTemplate, setPromptTemplate] = useState("");
  const [ruleset, setRuleset] = useState("{}");
  const [timeoutSeconds, setTimeoutSeconds] = useState("300");
  const [maxRetries, setMaxRetries] = useState("2");
  const [isShared, setIsShared] = useState("false");

  useEffect(() => {
    if (preset) {
      setName(preset.name);
      setPromptTemplate(preset.prompt_template || "");
      setRuleset(JSON.stringify(preset.ruleset, null, 2));
      setTimeoutSeconds(String(preset.timeout_seconds));
      setMaxRetries(String(preset.max_retries));
      setIsShared(String(preset.is_shared));
    }
  }, [preset]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-muted-foreground">로딩 중...</p>
      </div>
    );
  }
  if (error) throw error;
  if (!preset) return null;

  const handleSave = async () => {
    let parsedRuleset: Record<string, unknown> = {};
    try {
      parsedRuleset = JSON.parse(ruleset);
    } catch {
      return;
    }
    await updatePreset.mutateAsync({
      id,
      data: {
        name,
        prompt_template: promptTemplate || undefined,
        ruleset: parsedRuleset,
        timeout_seconds: parseInt(timeoutSeconds) || 300,
        max_retries: parseInt(maxRetries) || 2,
        is_shared: isShared === "true",
      },
    });
    setEditing(false);
  };

  const handleDelete = async () => {
    await deletePreset.mutateAsync(id);
    router.push("/presets");
  };

  return (
    <div className="mx-auto max-w-3xl p-6 space-y-6">
      <div className="space-y-1">
        <Link
          href="/presets"
          className="text-sm text-muted-foreground hover:underline"
        >
          &larr; 프리셋 목록
        </Link>
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold">{preset.name}</h1>
          <Badge variant={preset.is_shared ? "default" : "outline"}>
            {preset.is_shared ? "공유" : "개인"}
          </Badge>
        </div>
      </div>

      {!editing ? (
        <>
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium text-muted-foreground">
                설정
              </CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-2 gap-y-3 gap-x-6 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">에이전트 ID</span>
                <span className="font-mono text-xs">{preset.agent_id.slice(0, 8)}...</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">버전 SHA</span>
                <span className="font-mono text-xs">{preset.version_sha}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">타임아웃</span>
                <span>{preset.timeout_seconds}초</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">최대 재시도</span>
                <span>{preset.max_retries}회</span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium text-muted-foreground">
                프롬프트 템플릿
              </CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="rounded bg-muted p-3 font-mono text-xs whitespace-pre-wrap">
                {preset.prompt_template || "(없음)"}
              </pre>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium text-muted-foreground">
                룰셋
              </CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="rounded bg-muted p-3 font-mono text-xs overflow-x-auto">
                {JSON.stringify(preset.ruleset, null, 2)}
              </pre>
            </CardContent>
          </Card>

          <div className="flex gap-2">
            <Button onClick={() => setEditing(true)}>편집</Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={deletePreset.isPending}
            >
              {deletePreset.isPending ? "삭제 중..." : "삭제"}
            </Button>
          </div>
        </>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground">
              프리셋 편집
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">이름</Label>
              <Input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="prompt">프롬프트 템플릿</Label>
              <textarea
                id="prompt"
                value={promptTemplate}
                onChange={(e) => setPromptTemplate(e.target.value)}
                className="flex min-h-[100px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="ruleset">룰셋 (JSON)</Label>
              <textarea
                id="ruleset"
                value={ruleset}
                onChange={(e) => setRuleset(e.target.value)}
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

            {updatePreset.error && (
              <p className="text-xs text-[#ff5555]">
                {updatePreset.error instanceof Error ? updatePreset.error.message : "저장 실패"}
              </p>
            )}

            <div className="flex gap-2">
              <Button
                disabled={updatePreset.isPending || !name}
                onClick={handleSave}
              >
                {updatePreset.isPending ? "저장 중..." : "저장"}
              </Button>
              <Button variant="outline" onClick={() => setEditing(false)}>
                취소
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
