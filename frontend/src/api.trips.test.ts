import { beforeEach, describe, expect, it, vi } from 'vitest';
import axios from 'axios';
import {
  deletePlan,
  fetchPlans,
  loadTripIds,
  refreshPlan,
  removeTripId,
  saveTripId,
} from './api';

vi.mock('axios', () => ({
  default: { delete: vi.fn(), get: vi.fn(), post: vi.fn() },
}));

const memory = new Map<string, string>();

beforeEach(() => {
  memory.clear();
  vi.stubGlobal('localStorage', {
    getItem: (key: string) => memory.get(key) ?? null,
    setItem: (key: string, value: string) => void memory.set(key, value),
    removeItem: (key: string) => void memory.delete(key),
  });
  vi.mocked(axios.get).mockReset();
  vi.mocked(axios.post).mockReset();
  vi.mocked(axios.delete).mockReset();
});

describe('trip id storage', () => {
  it('starts empty and saves newest-first without duplicates, capped at 30', () => {
    expect(loadTripIds()).toEqual([]);
    saveTripId('a');
    saveTripId('b');
    saveTripId('a');
    expect(loadTripIds()).toEqual(['a', 'b']);
    for (let i = 0; i < 40; i++) saveTripId(`id-${i}`);
    expect(loadTripIds()).toHaveLength(30);
    expect(loadTripIds()[0]).toBe('id-39');
  });

  it('removes ids and tolerates corrupt storage', () => {
    saveTripId('a');
    saveTripId('b');
    expect(removeTripId('a')).toEqual(['b']);
    memory.set('stellinerary-trips', 'not-json{{{');
    expect(loadTripIds()).toEqual([]);
  });
});

describe('trip endpoints', () => {
  it('lists plans from the backend', async () => {
    vi.mocked(axios.get).mockResolvedValueOnce({ data: [] });
    await fetchPlans();
    expect(axios.get).toHaveBeenCalledWith('http://localhost:8000/plans', { headers: {} });
  });

  it('refreshes a plan by id', async () => {
    vi.mocked(axios.post).mockResolvedValueOnce({ data: { plan_id: 'p1' } });
    await refreshPlan('p1');
    expect(axios.post).toHaveBeenCalledWith(
      'http://localhost:8000/plans/p1/refresh',
      {},
      { headers: {} },
    );
  });

  it('deletes a plan by id', async () => {
    vi.mocked(axios.delete).mockResolvedValueOnce({ data: { deleted: 'p1' } });
    await deletePlan('p1');
    expect(axios.delete).toHaveBeenCalledWith('http://localhost:8000/plans/p1', { headers: {} });
  });
});
