"use client";

import { useState } from "react";
import { useComments, useCreateComment } from "@/lib/hooks/use-comments";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface Props {
  findingId: string | null;
}

export function CommentList({ findingId }: Props) {
  const { data: comments } = useComments(findingId);
  const createComment = useCreateComment(findingId);
  const [content, setContent] = useState("");

  if (!findingId) return null;

  const handleSubmit = async () => {
    if (!content.trim()) return;
    await createComment.mutateAsync(content.trim());
    setContent("");
  };

  return (
    <div className="space-y-3">
      <h4 className="text-xs font-semibold text-muted-foreground uppercase">
        코멘트
      </h4>

      <div className="space-y-2 max-h-40 overflow-y-auto">
        {!comments || comments.length === 0 ? (
          <p className="text-xs text-muted-foreground">코멘트 없음</p>
        ) : (
          comments.map((c) => (
            <div key={c.id} className="rounded bg-muted/50 p-2 text-sm">
              <div className="flex items-center justify-between mb-1">
                <span className="font-mono text-xs text-muted-foreground">
                  {c.author_id.slice(0, 8)}
                </span>
                <span className="text-xs text-muted-foreground">
                  {new Date(c.created_at).toLocaleString("ko-KR")}
                </span>
              </div>
              <p className="text-sm">{c.content}</p>
            </div>
          ))
        )}
      </div>

      <div className="flex gap-2">
        <Input
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="코멘트 작성..."
          className="text-sm"
        />
        <Button
          size="sm"
          disabled={createComment.isPending || !content.trim()}
          onClick={handleSubmit}
        >
          등록
        </Button>
      </div>
    </div>
  );
}
