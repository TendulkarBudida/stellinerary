import { describe, expect, it, vi } from 'vitest';
import axios from 'axios';
import { fetchPlan, normaliseApiBase } from './api';

vi.mock('axios', () => ({
    default: { post: vi.fn() },
}));

describe('frontend API configuration', () => {
    it('uses localhost when no backend URL is configured', () => {
        expect(normaliseApiBase()).toBe('http://localhost:8000');
    });

    it('removes trailing slashes from a configured backend URL', () => {
        expect(normaliseApiBase('https://api.example.com///')).toBe('https://api.example.com');
    });

    it('posts a plan request to the configured API base', async () => {
        const response = { data: { chosen_site: null } };
        vi.mocked(axios.post).mockResolvedValueOnce(response);

        const request = {
            user_lat: 12.9716,
            user_lon: 77.5946,
            date_start: '2026-12-13',
            date_end: '2026-12-14',
            equipment_level: 'naked_eye' as const,
        };

        await fetchPlan(request);

        expect(axios.post).toHaveBeenCalledWith('http://localhost:8000/plan', request);
    });

    it('propagates backend request failures to the caller', async () => {
        const error = new Error('backend unavailable');
        vi.mocked(axios.post).mockRejectedValueOnce(error);

        await expect(fetchPlan({
            user_lat: 12.9716,
            user_lon: 77.5946,
            date_start: '2026-12-13',
            date_end: '2026-12-14',
            equipment_level: 'naked_eye',
        })).rejects.toThrow('backend unavailable');
    });
});