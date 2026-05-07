'use client';

import { useRouter } from 'next/navigation';
import { useState, type FormEvent } from 'react';
import { useCreateProject } from '@/lib/hooks/use-projects';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

export default function NewProjectPage() {
  const router = useRouter();
  const createProject = useCreateProject();
  const [name, setName] = useState('');
  const [gitlabId, setGitlabId] = useState('');
  const [priority, setPriority] = useState('normal');
  const [deadline, setDeadline] = useState('');

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    await createProject.mutateAsync({
      name,
      gitlab_project_id: gitlabId,
      priority,
      deadline: deadline || null,
    });
    router.push('/projects');
  };

  return (
    <div className="mx-auto max-w-2xl p-6">
      <Card>
        <CardHeader>
          <CardTitle>새 프로젝트 등록</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">프로젝트 이름</Label>
              <Input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="gitlab">GitLab 프로젝트 ID</Label>
              <Input
                id="gitlab"
                value={gitlabId}
                onChange={(e) => setGitlabId(e.target.value)}
                placeholder="group/project-name"
                required
              />
            </div>
            <div className="space-y-2">
              <Label>우선순위</Label>
              <Select value={priority} onValueChange={(v) => setPriority(v ?? 'normal')}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="urgent">긴급</SelectItem>
                  <SelectItem value="high">높음</SelectItem>
                  <SelectItem value="normal">보통</SelectItem>
                  <SelectItem value="low">낮음</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="deadline">마감일</Label>
              <Input
                id="deadline"
                type="date"
                value={deadline}
                onChange={(e) => setDeadline(e.target.value)}
              />
            </div>
            <div className="flex gap-2">
              <Button type="submit" disabled={createProject.isPending}>
                {createProject.isPending ? '등록 중...' : '등록'}
              </Button>
              <Button type="button" variant="outline" onClick={() => router.back()}>
                취소
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
