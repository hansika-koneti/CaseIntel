/**
 * CaseIntel — System API Client
 * Checks real backend connectivity and live service status.
 */

import { apiFetch } from './client';

export interface SystemHealthResponse {
  status: string;
  mode: string;
  services?: Record<string, string>;
}

export async function checkSystemHealth(): Promise<SystemHealthResponse> {
  return apiFetch<SystemHealthResponse>('/api/health');
}
