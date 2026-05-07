'use client';

import { useQuery } from '@tanstack/react-query';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { apiFetch } from '@/lib/api/client';

interface User {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'lead' | 'reviewer' | 'viewer';
  created_at: string;
}

const ROLE_LABEL: Record<string, { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline' }> = {
  admin: { label: 'Admin', variant: 'destructive' },
  lead: { label: 'Lead', variant: 'default' },
  reviewer: { label: 'Reviewer', variant: 'secondary' },
  viewer: { label: 'Viewer', variant: 'outline' },
};

export default function UsersPage() {
  const { data: users, isLoading } = useQuery({
    queryKey: ['users'],
    queryFn: () => apiFetch<User[]>('/users'),
  });

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold">사용자/권한 관리</h2>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium text-muted-foreground">
            권한 매트릭스
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>기능</TableHead>
                <TableHead>Viewer</TableHead>
                <TableHead>Reviewer</TableHead>
                <TableHead>Lead</TableHead>
                <TableHead>Admin</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {[
                ['프로젝트 조회', true, true, true, true],
                ['발견 조회', true, true, true, true],
                ['발견 검증', false, true, true, true],
                ['코멘트 작성', false, true, true, true],
                ['분석 실행', false, true, true, true],
                ['프리셋 관리', false, false, true, true],
                ['사용자 관리', false, false, false, true],
                ['감사 로그', false, false, false, true],
              ].map(([label, ...perms]) => (
                <TableRow key={label as string}>
                  <TableCell className="text-xs">{label as string}</TableCell>
                  {(perms as boolean[]).map((ok, i) => (
                    <TableCell key={i} className="text-center text-xs">
                      {ok ? '✓' : '—'}
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium text-muted-foreground">사용자 목록</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-sm text-muted-foreground">로딩 중...</p>
          ) : !users?.length ? (
            <p className="text-sm text-muted-foreground">사용자가 없습니다.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>이름</TableHead>
                  <TableHead>이메일</TableHead>
                  <TableHead>역할</TableHead>
                  <TableHead>가입일</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {users.map((u) => {
                  const roleConfig = ROLE_LABEL[u.role] ?? { label: u.role, variant: 'outline' as const };
                  return (
                    <TableRow key={u.id}>
                      <TableCell>{u.name}</TableCell>
                      <TableCell className="text-xs">{u.email}</TableCell>
                      <TableCell>
                        <Badge variant={roleConfig.variant}>{roleConfig.label}</Badge>
                      </TableCell>
                      <TableCell className="text-xs">
                        {new Date(u.created_at).toLocaleDateString('ko-KR')}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
