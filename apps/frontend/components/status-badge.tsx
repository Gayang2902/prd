import { Badge } from '@/components/ui/badge';

const STATUS_CONFIG: Record<string, { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline' }> = {
  pending: { label: '대기', variant: 'secondary' },
  in_progress: { label: '분석중', variant: 'default' },
  in_review: { label: '검증중', variant: 'outline' },
  completed: { label: '완료', variant: 'secondary' },
  on_hold: { label: '보류', variant: 'destructive' },
};

const PRIORITY_CONFIG: Record<string, { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline' }> = {
  urgent: { label: '긴급', variant: 'destructive' },
  high: { label: '높음', variant: 'default' },
  normal: { label: '보통', variant: 'secondary' },
  low: { label: '낮음', variant: 'outline' },
};

export function StatusBadge({ status }: { status: string }) {
  const config = STATUS_CONFIG[status] ?? { label: status, variant: 'outline' as const };
  return <Badge variant={config.variant}>{config.label}</Badge>;
}

export function PriorityBadge({ priority }: { priority: string }) {
  const config = PRIORITY_CONFIG[priority] ?? { label: priority, variant: 'outline' as const };
  return <Badge variant={config.variant}>{config.label}</Badge>;
}
