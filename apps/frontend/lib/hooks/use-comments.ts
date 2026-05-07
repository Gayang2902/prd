"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createComment, fetchComments } from "../api/comments";

export function useComments(findingId: string | null) {
  return useQuery({
    queryKey: ["comments", findingId],
    queryFn: () => fetchComments(findingId!),
    enabled: !!findingId,
  });
}

export function useCreateComment(findingId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (content: string) => createComment(findingId!, content),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["comments", findingId] }),
  });
}
