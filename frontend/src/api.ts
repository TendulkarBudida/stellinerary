import axios from 'axios';
import type { PlanRequest, ExpeditionPlan } from './types';

export const normaliseApiBase = (value?: string): string =>
    (value || 'http://localhost:8000').replace(/\/+$/, '');

const API_BASE = normaliseApiBase(import.meta.env.VITE_API_BASE_URL);

export const fetchPlan = async (request: PlanRequest): Promise<ExpeditionPlan> => {
    const response = await axios.post<ExpeditionPlan>(`${API_BASE}/plan`, request);
    return response.data;
};

export const fetchPlanById = async (planId: string): Promise<ExpeditionPlan> => {
    const response = await axios.get<ExpeditionPlan>(`${API_BASE}/plans/${planId}`);
    return response.data;
};

export const refreshPlan = async (planId: string): Promise<ExpeditionPlan> => {
    const response = await axios.post<ExpeditionPlan>(`${API_BASE}/plans/${planId}/refresh`);
    return response.data;
};

export interface PlanSummary {
    plan_id: string;
    observation_end?: string;
    updated_at?: string | null;
    site_name?: string | null;
    date_start?: string;
}

export const fetchPlans = async (): Promise<PlanSummary[]> => {
    const response = await axios.get<PlanSummary[]>(`${API_BASE}/plans`);
    return response.data;
};

const TRIPS_KEY = 'stellinerary-trips';

export const loadTripIds = (): string[] => {
    try {
        const raw = localStorage.getItem(TRIPS_KEY);
        const parsed: unknown = raw ? JSON.parse(raw) : [];
        return Array.isArray(parsed) ? parsed.filter((v): v is string => typeof v === 'string') : [];
    } catch {
        return [];
    }
};

export const saveTripId = (planId: string): string[] => {
    const ids = [planId, ...loadTripIds().filter((id) => id !== planId)].slice(0, 30);
    try {
        localStorage.setItem(TRIPS_KEY, JSON.stringify(ids));
    } catch {
        /* storage unavailable — trips just won't persist */
    }
    return ids;
};

export const removeTripId = (planId: string): string[] => {
    const ids = loadTripIds().filter((id) => id !== planId);
    try {
        localStorage.setItem(TRIPS_KEY, JSON.stringify(ids));
    } catch {
        /* ignore */
    }
    return ids;
};
