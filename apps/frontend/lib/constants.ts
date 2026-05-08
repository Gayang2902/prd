import type { Session } from "@/lib/api/sessions";

export const SESSION_TYPE_LABEL: Record<string, string> = {
  static_analysis: "정적 분석",
  target_discovery: "타겟 디스커버리",
  zero_day_hunting: "제로데이 헌팅",
};

export const TARGET_PHASES = [
  "gathering",
  "filtering",
  "scoring",
  "shortlisting",
  "complete",
] as const;

export const TARGET_LABELS: Record<string, string> = {
  gathering: "수집",
  filtering: "필터링",
  scoring: "스코어링",
  shortlisting: "숏리스트",
  complete: "완료",
};

export const HUNTING_PHASES = [
  "setup",
  "fuzzing",
  "triage",
  "code_reading",
  "bypass",
  "cross_verify",
  "complete",
] as const;

export const HUNTING_LABELS: Record<string, string> = {
  setup: "셋업",
  fuzzing: "퍼징",
  triage: "트리아지",
  code_reading: "코드 리딩",
  bypass: "우회",
  cross_verify: "교차 검증",
  complete: "완료",
};

export function getPhaseConfig(session: Session) {
  if (session.session_type === "target_discovery") {
    return { order: TARGET_PHASES as unknown as string[], labels: TARGET_LABELS };
  }
  return { order: HUNTING_PHASES as unknown as string[], labels: HUNTING_LABELS };
}
