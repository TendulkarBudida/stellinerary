import axios from 'axios';
import type { PlanRequest, ExpeditionPlan } from './types';

const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '');

export const fetchPlan = async (request: PlanRequest): Promise<ExpeditionPlan> => {
    const response = await axios.post<ExpeditionPlan>(`${API_BASE}/plan`, request);
    return response.data;
};
