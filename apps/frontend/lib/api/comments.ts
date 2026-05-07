import { apiFetch } from './client';

export interface Comment {
  id: string;
  finding_id: string;
  author_id: string;
  content: string;
  created_at: string;
}

export function fetchComments(findingId: string): Promise<Comment[]> {
  return apiFetch<Comment[]>(`/findings/${findingId}/comments`);
}

export function createComment(findingId: string, content: string): Promise<Comment> {
  return apiFetch<Comment>(`/findings/${findingId}/comments`, {
    method: 'POST',
    body: JSON.stringify({ content }),
  });
}
