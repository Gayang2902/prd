import { apiFetch } from './client';

export interface Project {
  id: string;
  name: string;
  gitlab_project_id: string;
  owner_id: string;
  priority: 'urgent' | 'high' | 'normal' | 'low';
  status: 'pending' | 'in_progress' | 'in_review' | 'completed' | 'on_hold';
  deadline: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectCreate {
  name: string;
  gitlab_project_id: string;
  priority?: string;
  deadline?: string | null;
}

export function fetchProjects(params?: { status?: string; owner_id?: string }): Promise<Project[]> {
  const query = new URLSearchParams();
  if (params?.status) query.set('status', params.status);
  if (params?.owner_id) query.set('owner_id', params.owner_id);
  const qs = query.toString();
  return apiFetch<Project[]>(`/projects${qs ? `?${qs}` : ''}`);
}

export function fetchProject(id: string): Promise<Project> {
  return apiFetch<Project>(`/projects/${id}`);
}

export function createProject(data: ProjectCreate): Promise<Project> {
  return apiFetch<Project>('/projects', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export function updateProject(id: string, data: Partial<Project>): Promise<Project> {
  return apiFetch<Project>(`/projects/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}
