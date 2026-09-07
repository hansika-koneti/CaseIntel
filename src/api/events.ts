/**
 * CaseIntel — Events API
 *
 * Typed wrappers for GET /api/events and GET /api/events/{id}.
 * The backend returns snake_case which the client normalises to camelCase.
 */

import { apiFetch } from './client';
import type { InvestigationEvent, Evidence } from '../types';

// ── Response shape from GET /api/events ───────────────────────────────────
interface EventsResponse {
  events: InvestigationEvent[];
  evidence: Evidence[];
  total: number;
  investigationId: string | null;
}

/**
 * GET /api/events?investigation_id=&entity_id=&suspicious_only=
 */
export async function getEvents(params?: {
  investigationId?: string;
  entityId?: string;
  suspiciousOnly?: boolean;
}): Promise<{ events: InvestigationEvent[]; evidence: Evidence[] }> {
  const qs = new URLSearchParams();
  if (params?.investigationId) qs.set('investigation_id', params.investigationId);
  if (params?.entityId) qs.set('entity_id', params.entityId);
  if (params?.suspiciousOnly) qs.set('suspicious_only', 'true');

  const path = `/api/events/${qs.toString() ? `?${qs}` : ''}`;
  const data = await apiFetch<EventsResponse>(path);
  return { events: data.events, evidence: data.evidence };
}

/**
 * GET /api/events/{event_id}
 */
export async function getEvent(eventId: string): Promise<InvestigationEvent> {
  return apiFetch<InvestigationEvent>(`/api/events/${eventId}`);
}
