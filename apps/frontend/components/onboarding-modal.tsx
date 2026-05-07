'use client';

import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

const STEPS = [
  {
    title: 'SecureScope에 오신 것을 환영합니다',
    body: 'AI 기반 코드 보안 검수 플랫폼입니다. 프로젝트를 등록하고, 분석을 실행하고, 발견된 취약점을 검증하세요.',
  },
  {
    title: '1. 프로젝트 등록',
    body: 'GitLab 프로젝트를 연결하면 브랜치/커밋 단위로 분석을 실행할 수 있습니다.',
  },
  {
    title: '2. 분석 실행',
    body: '에이전트(Claude Code, Codex)와 프리셋을 선택해 분석을 시작하세요. 큐에서 순서를 확인할 수 있습니다.',
  },
  {
    title: '3. 취약점 검증',
    body: '발견된 취약점을 코드와 함께 확인하고, 확정/오탐/검토 판정을 부여하세요. 단축키(j/k/c/f/r)를 지원합니다.',
  },
] as const;

const ONBOARDING_KEY = 'securescope_onboarding_done';

export function OnboardingModal() {
  const [visible, setVisible] = useState(false);
  const [step, setStep] = useState(0);

  useEffect(() => {
    if (!localStorage.getItem(ONBOARDING_KEY)) {
      setVisible(true);
    }
  }, []);

  if (!visible) return null;

  const current = STEPS[step];
  const isLast = step === STEPS.length - 1;

  function dismiss() {
    localStorage.setItem(ONBOARDING_KEY, '1');
    setVisible(false);
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <Card className="max-w-lg w-full mx-4">
        <CardHeader>
          <CardTitle>{current.title}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">{current.body}</p>
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">
              {step + 1} / {STEPS.length}
            </span>
            <div className="flex gap-2">
              <Button variant="ghost" size="sm" onClick={dismiss}>
                건너뛰기
              </Button>
              {isLast ? (
                <Button size="sm" onClick={dismiss}>
                  시작하기
                </Button>
              ) : (
                <Button size="sm" onClick={() => setStep(step + 1)}>
                  다음
                </Button>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
