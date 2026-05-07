'use client';

import { useState, type FormEvent } from 'react';
import { useCreateSession } from '@/lib/hooks/use-sessions';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

interface Props {
  projectId: string;
}

export function NewSessionDialog({ projectId }: Props) {
  const [open, setOpen] = useState(false);
  const [branch, setBranch] = useState('');
  const [commitSha, setCommitSha] = useState('');
  const createSession = useCreateSession(projectId);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    await createSession.mutateAsync({
      branch,
      commit_sha: commitSha || null,
      preset_id: '00000000-0000-0000-0000-000000000001',
      agent_id: '00000000-0000-0000-0000-000000000001',
    });
    setOpen(false);
    setBranch('');
    setCommitSha('');
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger>
        <Button>분석 실행</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>새 분석 실행</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="branch">브랜치</Label>
            <Input
              id="branch"
              value={branch}
              onChange={(e) => setBranch(e.target.value)}
              placeholder="main, release-1.4, feat/login..."
              required
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="commit">커밋 SHA (선택)</Label>
            <Input
              id="commit"
              value={commitSha}
              onChange={(e) => setCommitSha(e.target.value)}
              placeholder="비워두면 HEAD 사용"
            />
          </div>
          <Button type="submit" className="w-full" disabled={createSession.isPending}>
            {createSession.isPending ? '실행 중...' : '분석 시작'}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
