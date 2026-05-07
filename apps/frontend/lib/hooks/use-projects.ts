'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  createProject,
  fetchProject,
  fetchProjects,
  updateProject,
  type Project,
  type ProjectCreate,
} from '../api/projects';

export function useProjects(params?: { status?: string }) {
  return useQuery({
    queryKey: ['projects', params],
    queryFn: () => fetchProjects(params),
  });
}

export function useProject(id: string) {
  return useQuery({
    queryKey: ['projects', id],
    queryFn: () => fetchProject(id),
  });
}

export function useCreateProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ProjectCreate) => createProject(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['projects'] }),
  });
}

export function useUpdateProject(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Partial<Project>) => updateProject(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['projects'] });
      qc.invalidateQueries({ queryKey: ['projects', id] });
    },
  });
}
