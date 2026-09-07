/**
 * CaseIntel — Reports API
 *
 * Typed client wrapper for generating and retrieving LLM-assisted investigation reports.
 */

import { apiFetch } from './client';
import type { Report } from '../types';

export interface GenerateReportResponse {
  status: string;
  report: Report;
}

/**
 * Fetch report for an investigation.
 */
export async function getReport(investigationId: string): Promise<Report> {
  return apiFetch<Report>(`/api/reports/${investigationId}`);
}

/**
 * Generate a new report for an active investigation.
 */
export async function generateReport(investigationId: string): Promise<GenerateReportResponse> {
  return apiFetch<GenerateReportResponse>(`/api/reports/${investigationId}/generate`, {
    method: 'POST',
  });
}
