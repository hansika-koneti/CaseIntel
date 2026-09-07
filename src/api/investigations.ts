/**
 * CaseIntel — Investigations API
 *
 * Typed wrappers for all investigation-related FastAPI endpoints.
 * All functions return camelCase-normalised objects that match the
 * frontend TypeScript types in src/types/index.ts.
 */

import { apiFetch } from './client';
import type { Investigation } from '../types';

// ── Investigation list item (summary) ─────────────────────────────────────
// Mirrors the InvestigationItem interface in InvestigationsPage.tsx
export interface InvestigationSummary {
  id: string;
  caseNumber: string;
  status: 'under_investigation' | 'closed' | 'pending' | 'escalated' | 'processing';
  incidentType: string;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  confidence: number;
  location: string;
  createdAt: string;
  investigator: string;
  videoCount: number;
}

// Shape for creating a new investigation (matches InvestigationCreateRequest on the backend)
export interface CreateInvestigationPayload {
  caseNumber: string;
  incidentType: string;
  location: string;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  status: 'under_investigation' | 'closed' | 'pending';
  videoCount: number;
  confidence: number;
  investigator: string;
}

// ── API response wrapper from GET /api/investigations ─────────────────────
interface ListResponse {
  investigations: InvestigationSummary[];
  total: number;
}

// ── Endpoints ─────────────────────────────────────────────────────────────

/**
 * GET /api/investigations
 * Returns the full list of investigation summaries.
 */
export async function getInvestigations(): Promise<InvestigationSummary[]> {
  const data = await apiFetch<ListResponse>('/api/investigations/');
  return data.investigations;
}

/**
 * POST /api/investigations
 * Creates a new investigation and returns the persisted summary.
 */
export async function createInvestigation(
  payload: CreateInvestigationPayload,
): Promise<InvestigationSummary> {
  return apiFetch<InvestigationSummary>('/api/investigations/', {
    method: 'POST',
    body: payload,
  });
}

/**
 * GET /api/investigations/{id}
 * Returns the full investigation detail (entities, events, evidence, report).
 */
export async function getInvestigation(id: string): Promise<Investigation> {
  return apiFetch<Investigation>(`/api/investigations/${id}`);
}

/**
 * POST /api/investigations/{id}/set-active-video/{videoId}
 * Explicitly sets and validates the active video for the investigation.
 */
export async function setActiveVideo(
  investigationId: string,
  videoId: string,
): Promise<{ success: boolean; investigationId: string; activeVideoId: string; filename: string }> {
  return apiFetch<{ success: boolean; investigationId: string; activeVideoId: string; filename: string }>(
    `/api/investigations/${investigationId}/set-active-video/${videoId}`,
    {
      method: 'POST',
    },
  );
}

