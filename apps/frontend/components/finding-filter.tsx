'use client';

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

const SEVERITIES = ['all', 'critical', 'high', 'medium', 'low', 'info'] as const;
const SEVERITY_LABELS: Record<string, string> = {
  all: '전체 심각도',
  critical: 'Critical',
  high: 'High',
  medium: 'Medium',
  low: 'Low',
  info: 'Info',
};

interface Props {
  severity: string;
  onSeverityChange: (v: string) => void;
  category: string;
  onCategoryChange: (v: string) => void;
  categories: string[];
}

export function FindingFilter({
  severity,
  onSeverityChange,
  category,
  onCategoryChange,
  categories,
}: Props) {
  return (
    <div className="flex gap-2">
      <Select value={severity} onValueChange={(v) => onSeverityChange(v ?? 'all')}>
        <SelectTrigger className="w-[140px] h-8 text-xs">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {SEVERITIES.map((s) => (
            <SelectItem key={s} value={s}>
              {SEVERITY_LABELS[s]}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select value={category} onValueChange={(v) => onCategoryChange(v ?? 'all')}>
        <SelectTrigger className="w-[160px] h-8 text-xs">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">전체 카테고리</SelectItem>
          {categories.map((c) => (
            <SelectItem key={c} value={c}>
              {c}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
