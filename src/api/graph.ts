/**
 * CaseIntel — Knowledge Graph API
 *
 * Typed client wrapper for querying the Neo4j / dynamic graph representation of an investigation.
 */

import { apiFetch } from './client';

export interface GraphNodePayload {
  id: string;
  label: string;
  type: string;
  category?: 'primary' | 'secondary' | 'context' | 'technical';
  is_technical?: boolean;
  confidence?: number;
  x: number;
  y: number;
  data?: Record<string, any>;
}

export interface GraphEdgePayload {
  id: string;
  source: string;
  target: string;
  relationship: string;
  label?: string;
  suspicious?: boolean;
  reason?: string;
  category?: string;
  is_technical?: boolean;
}

export interface KnowledgeGraphSummary {
  subjects?: number;
  cameras?: number;
  locations?: number;
  events?: number;
  suspicious_events?: number;
}

export interface KnowledgeGraphResponse {
  investigationId: string;
  caseNumber?: string;
  nodes: GraphNodePayload[];
  edges: GraphEdgePayload[];
  entityDetails?: Record<string, any>;
  summary?: KnowledgeGraphSummary;
  neo4jConnected?: boolean;
}

/**
 * Fetch knowledge graph structure for an active investigation.
 */
export async function getKnowledgeGraph(
  investigationId: string,
): Promise<KnowledgeGraphResponse> {
  const json = await apiFetch<any>(`/api/knowledge-graph/${investigationId}`);
  return {
    investigationId: json.investigation_id || json.investigationId || investigationId,
    caseNumber: json.case_number || json.caseNumber,
    nodes: json.nodes || [],
    edges: json.edges || [],
    entityDetails: json.entity_details || json.entityDetails || {},
    summary: json.summary || {},
    neo4jConnected: json.neo4j_connected ?? json.neo4jConnected ?? false,
  };
}
