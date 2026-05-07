"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export default function IntegrationsPage() {
  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold">연동 설정</h2>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium text-muted-foreground">
            GitLab 연동
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm">GitLab API</span>
            <Badge variant="outline">설정 필요</Badge>
          </div>
          <p className="text-xs text-muted-foreground">
            Vault에 GitLab API 토큰을 등록하면 자동으로 연결됩니다.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium text-muted-foreground">
            알림 채널
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm">Slack Webhook</span>
            <Badge variant="outline">미설정</Badge>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm">Email (SMTP)</span>
            <Badge variant="outline">미설정</Badge>
          </div>
          <p className="text-xs text-muted-foreground">
            알림 트리거: 분석 완료, 분석 실패, 예산 초과, Critical 발견
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium text-muted-foreground">
            에이전트
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm">Claude Code</span>
            <Badge variant="secondary">등록됨</Badge>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm">Codex</span>
            <Badge variant="secondary">등록됨</Badge>
          </div>
          <p className="text-xs text-muted-foreground">
            에이전트는 pyproject.toml entry-point로 자동 발견됩니다.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
