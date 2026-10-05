import axios from 'axios';
import type { PlanRequest, ExpeditionPlan } from './types';

export const normaliseApiBase = (value?: string): string =>
    (value || 'http://localhost:8000').replace(/\/+$/, '');

const API_BASE = normaliseApiBase(import.meta.env.VITE_API_BASE_URL);

export const fetchPlan = async (request: PlanRequest): Promise<ExpeditionPlan> => {
    const response = await axios.post<ExpeditionPlan>(`${API_BASE}/plan`, request);
    return response.data;
};
