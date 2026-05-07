'use client';

import Link from 'next/link';
import { useProjects } from '@/lib/hooks/use-projects';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { StatusBadge, PriorityBadge } from '@/components/status-badge';
import { StatCard } from '@/components/stat-card';

export default function ProjectsPage() {
  const { data: projects, isLoading, error } = useProjects();

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-muted-foreground">로딩 중...</p>
      </div>
    );
  }

  if (error) throw error;

  const total = projects?.length ?? 0;
  const inProgress = projects?.filter((p) => p.status === 'in_progress').length ?? 0;
  const completed = projects?.filter((p) => p.status === 'completed').length ?? 0;

  return (
    <div className="mx-auto max-w-7xl p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">프로젝트</h1>
        <Link href="/projects/new">
          <Button>새 프로젝트</Button>
        </Link>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <StatCard title="전체" value={total} />
        <StatCard title="분석중" value={inProgress} />
        <StatCard title="완료" value={completed} />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>프로젝트 목록</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>이름</TableHead>
                <TableHead>상태</TableHead>
                <TableHead>우선순위</TableHead>
                <TableHead>마감일</TableHead>
                <TableHead>생성일</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {projects?.map((project) => (
                <TableRow key={project.id}>
                  <TableCell>
                    <Link href={`/projects/${project.id}`} className="font-medium hover:underline">
                      {project.name}
                    </Link>
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={project.status} />
                  </TableCell>
                  <TableCell>
                    <PriorityBadge priority={project.priority} />
                  </TableCell>
                  <TableCell>{project.deadline ?? '-'}</TableCell>
                  <TableCell>{new Date(project.created_at).toLocaleDateString('ko-KR')}</TableCell>
                </TableRow>
              ))}
              {total === 0 && (
                <TableRow>
                  <TableCell colSpan={5} className="text-center text-muted-foreground">
                    등록된 프로젝트가 없습니다.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
