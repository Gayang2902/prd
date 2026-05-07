"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export default function ProfilePage() {
  return (
    <div className="mx-auto max-w-2xl p-6 space-y-6">
      <h1 className="text-3xl font-bold">내 프로필</h1>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium text-muted-foreground">
            계정 정보
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-foreground">인증</span>
            <Badge variant="outline">X-User-Id (MVP)</Badge>
          </div>
          <p className="text-xs text-muted-foreground">
            SSO/OIDC 통합 후 자동으로 계정 정보가 표시됩니다.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium text-muted-foreground">
            단축키
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-2 text-sm">
            {[
              ["j / k", "이전 / 다음 발견"],
              ["c", "확정 (Confirmed)"],
              ["f", "오탐 (False Positive)"],
              ["r", "검토 필요 (Needs Review)"],
              ["e", "코드 확대"],
              ["?", "단축키 도움말"],
            ].map(([key, desc]) => (
              <div key={key} className="flex justify-between py-1">
                <kbd className="px-2 py-0.5 bg-muted rounded text-xs font-mono">
                  {key}
                </kbd>
                <span className="text-muted-foreground text-xs">{desc}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
