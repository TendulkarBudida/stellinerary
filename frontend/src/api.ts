import axios from 'axios';
import type { PlanRequest, ExpeditionPlan } from './types';

const API_BASE = 'http://localhost:8000';

export const fetchPlan = async (request: PlanRequest): Promise<ExpeditionPlan> => {
    const response = await axios.post<ExpeditionPlan>(`${API_BASE}/plan`, request);
    return response.data;
};
