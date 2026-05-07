import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('@/lib/api/client', () => ({
  apiFetch: vi.fn(),
}));

import { apiFetch } from '@/lib/api/client';
import { fetchPresets, fetchPreset, createPreset, updatePreset, deletePreset } from '@/lib/api/presets';
import { fetchComments, createComment } from '@/lib/api/comments';
import { fetchQueue } from '@/lib/api/queue';

const mockApiFetch = vi.mocked(apiFetch);

beforeEach(() => {
  mockApiFetch.mockReset();
});

describe('presets API', () => {
  it('fetchPresets without filter', async () => {
    mockApiFetch.mockResolvedValue([]);
    await fetchPresets();
    expect(mockApiFetch).toHaveBeenCalledWith('/presets');
  });

  it('fetchPresets with agent_id', async () => {
    mockApiFetch.mockResolvedValue([]);
    await fetchPresets('a1');
    expect(mockApiFetch).toHaveBeenCalledWith('/presets?agent_id=a1');
  });

  it('fetchPreset by id', async () => {
    mockApiFetch.mockResolvedValue({ id: 'pr1' });
    await fetchPreset('pr1');
    expect(mockApiFetch).toHaveBeenCalledWith('/presets/pr1');
  });

  it('createPreset sends POST', async () => {
    const data = { name: 'Test', agent_id: 'a1', version_sha: 'abc' };
    mockApiFetch.mockResolvedValue({ id: 'pr2', ...data });
    await createPreset(data);
    expect(mockApiFetch).toHaveBeenCalledWith('/presets', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  });

  it('updatePreset sends PATCH', async () => {
    const data = { name: 'Updated' };
    mockApiFetch.mockResolvedValue({ id: 'pr1', ...data });
    await updatePreset('pr1', data);
    expect(mockApiFetch).toHaveBeenCalledWith('/presets/pr1', {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  });

  it('deletePreset sends DELETE', async () => {
    mockApiFetch.mockResolvedValue(undefined);
    await deletePreset('pr1');
    expect(mockApiFetch).toHaveBeenCalledWith('/presets/pr1', { method: 'DELETE' });
  });
});

describe('comments API', () => {
  it('fetchComments', async () => {
    mockApiFetch.mockResolvedValue([]);
    await fetchComments('f1');
    expect(mockApiFetch).toHaveBeenCalledWith('/findings/f1/comments');
  });

  it('createComment sends POST', async () => {
    mockApiFetch.mockResolvedValue({ id: 'c1', content: 'test' });
    await createComment('f1', 'test');
    expect(mockApiFetch).toHaveBeenCalledWith('/findings/f1/comments', {
      method: 'POST',
      body: JSON.stringify({ content: 'test' }),
    });
  });
});

describe('queue API', () => {
  it('fetchQueue without filter', async () => {
    mockApiFetch.mockResolvedValue([]);
    await fetchQueue();
    expect(mockApiFetch).toHaveBeenCalledWith('/queue');
  });

  it('fetchQueue with state filter', async () => {
    mockApiFetch.mockResolvedValue([]);
    await fetchQueue('running');
    expect(mockApiFetch).toHaveBeenCalledWith('/queue?state=running');
  });
});
