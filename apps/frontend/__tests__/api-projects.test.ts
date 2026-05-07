import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('@/lib/api/client', () => ({
  apiFetch: vi.fn(),
}));

import { apiFetch } from '@/lib/api/client';
import { fetchProjects, fetchProject, createProject, updateProject } from '@/lib/api/projects';

const mockApiFetch = vi.mocked(apiFetch);

beforeEach(() => {
  mockApiFetch.mockReset();
});

describe('projects API', () => {
  it('fetchProjects without params', async () => {
    mockApiFetch.mockResolvedValue([]);
    await fetchProjects();
    expect(mockApiFetch).toHaveBeenCalledWith('/projects');
  });

  it('fetchProjects with status filter', async () => {
    mockApiFetch.mockResolvedValue([]);
    await fetchProjects({ status: 'in_progress' });
    expect(mockApiFetch).toHaveBeenCalledWith('/projects?status=in_progress');
  });

  it('fetchProjects with owner_id filter', async () => {
    mockApiFetch.mockResolvedValue([]);
    await fetchProjects({ owner_id: 'u1' });
    expect(mockApiFetch).toHaveBeenCalledWith('/projects?owner_id=u1');
  });

  it('fetchProject by id', async () => {
    const project = { id: 'p1', name: 'test' };
    mockApiFetch.mockResolvedValue(project);
    const result = await fetchProject('p1');
    expect(mockApiFetch).toHaveBeenCalledWith('/projects/p1');
    expect(result).toEqual(project);
  });

  it('createProject sends POST', async () => {
    const data = { name: 'New', gitlab_project_id: 'gl-1' };
    mockApiFetch.mockResolvedValue({ id: 'p2', ...data });
    await createProject(data);
    expect(mockApiFetch).toHaveBeenCalledWith('/projects', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  });

  it('updateProject sends PATCH', async () => {
    const data = { name: 'Updated' };
    mockApiFetch.mockResolvedValue({ id: 'p1', ...data });
    await updateProject('p1', data);
    expect(mockApiFetch).toHaveBeenCalledWith('/projects/p1', {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  });
});
