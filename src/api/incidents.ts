/**
 * CaseIntel — Incidents API
 *
 * Typed client wrappers for XGBoost incident prediction and TreeSHAP explainability.
 */

import { apiFetch } from './client';
import type { Severity } from '../types';

export interface FeatureContribution {
  featureName?: string;
  feature: string;
  rawValue?: number;
  value: string;
  shapValue?: number;
  contribution: number;
  impactDirection?: 'positive' | 'negative';
}

export interface ShapExplanationResponse {
  predictedClass: string;
  confidence: number;
  baseValue: number;
  featureContributions: FeatureContribution[];
  positiveContributors: FeatureContribution[];
  negativeContributors: FeatureContribution[];
  featureNames: string[];
  shapValuesVector: number[];
  narrative: string;
}

export interface IncidentClassificationResponse {
  type: string;
  severity: Severity;
  confidence: number;
  incidentRiskScore: number;
  classifierVersion: string;
  featureContributions: FeatureContribution[];
  classProbabilities: Record<string, number>;
  extractedFeatures: Record<string, number>;
  reasoning: string;
  investigationId?: string;
  caseNumber?: string;
  baseValue?: number;
  positiveContributors?: FeatureContribution[];
  negativeContributors?: FeatureContribution[];
  shapExplanation?: ShapExplanationResponse;
  status?: string;
  has_analysis?: boolean;
  hasAnalysis?: boolean;
  is_hypothesis?: boolean;
  isHypothesis?: boolean;
  theft_visually_verified?: boolean;
  theftVisuallyVerified?: boolean;
  hypothesis_status?: string;
  hypothesisStatus?: string;
  visual_evidence_summary?: string;
  visualEvidenceSummary?: string;
  forensic_rule_evaluation?: Array<{ step: number; name: string; status: string; detail: string }>;
  forensicRuleEvaluation?: Array<{ step: number; name: string; status: string; detail: string }>;
  verified_observations?: Array<{ action: string; confidence: number; severity: string; description: string; timestamp: string; entity_id: string }>;
  verifiedObservations?: Array<{ action: string; confidence: number; severity: string; description: string; timestamp: string; entity_id: string }>;
}

function mapShapContribution(item: any): FeatureContribution {
  return {
    featureName: item.featureName ?? item.feature_name,
    feature: item.feature,
    rawValue: item.rawValue ?? item.raw_value,
    value: item.value,
    shapValue: item.shapValue ?? item.shap_value,
    contribution: item.contribution,
    impactDirection: item.impactDirection ?? item.impact_direction,
  };
}

/**
 * Fetch XGBoost incident classification with TreeSHAP explainability for active investigation.
 */
export async function getIncidentAnalysis(
  investigationId: string,
): Promise<IncidentClassificationResponse> {
  const json = await apiFetch<any>(`/api/incidents/${investigationId}`);
  const rawContribs = json.featureContributions ?? json.feature_contributions ?? [];
  const featureContributions = rawContribs.map(mapShapContribution);
  const positiveContributors = (json.positiveContributors ?? json.positive_contributors ?? []).map(mapShapContribution);
  const negativeContributors = (json.negativeContributors ?? json.negative_contributors ?? []).map(mapShapContribution);

  const isHypo = Boolean(json.is_hypothesis ?? json.isHypothesis);
  const theftVerif = Boolean(json.theft_visually_verified ?? json.theftVisuallyVerified);
  const hypoStatus = json.hypothesis_status ?? json.hypothesisStatus;
  const visSummary = json.visual_evidence_summary ?? json.visualEvidenceSummary;
  const forensicRules = json.forensic_rule_evaluation ?? json.forensicRuleEvaluation ?? [];
  const verifiedObs = json.verified_observations ?? json.verifiedObservations ?? [];

  return {
    type: json.type,
    severity: json.severity as Severity,
    confidence: json.confidence,
    incidentRiskScore: json.incidentRiskScore ?? json.incident_risk_score ?? json.confidence,
    classifierVersion: json.classifierVersion ?? json.classifier_version ?? 'xgboost-1.8-caseintel',
    featureContributions,
    classProbabilities: json.classProbabilities ?? json.class_probabilities ?? {},
    extractedFeatures: json.extractedFeatures ?? json.extracted_features ?? {},
    reasoning: json.reasoning ?? '',
    investigationId: json.investigationId ?? json.investigation_id,
    caseNumber: json.caseNumber ?? json.case_number,
    baseValue: json.baseValue ?? json.base_value,
    positiveContributors,
    negativeContributors,
    shapExplanation: json.shapExplanation ?? json.shap_explanation,
    status: json.status,
    has_analysis: json.has_analysis,
    hasAnalysis: json.hasAnalysis,
    is_hypothesis: isHypo,
    isHypothesis: isHypo,
    theft_visually_verified: theftVerif,
    theftVisuallyVerified: theftVerif,
    hypothesis_status: hypoStatus,
    hypothesisStatus: hypoStatus,
    visual_evidence_summary: visSummary,
    visualEvidenceSummary: visSummary,
    forensic_rule_evaluation: forensicRules,
    forensicRuleEvaluation: forensicRules,
    verified_observations: verifiedObs,
    verifiedObservations: verifiedObs,
  };
}

/**
 * Fetch dedicated TreeSHAP explanation for investigation.
 */
export async function getShapExplanation(
  investigationId: string,
): Promise<ShapExplanationResponse> {
  const json = await apiFetch<any>(`/api/incidents/${investigationId}/shap`);
  return {
    predictedClass: json.predicted_class,
    confidence: json.confidence,
    baseValue: json.base_value,
    featureContributions: (json.feature_contributions || []).map(mapShapContribution),
    positiveContributors: (json.positive_contributors || []).map(mapShapContribution),
    negativeContributors: (json.negative_contributors || []).map(mapShapContribution),
    featureNames: json.feature_names || [],
    shapValuesVector: json.shap_values_vector || [],
    narrative: json.narrative || '',
  };
}

/**
 * Predict incident directly from custom tabular feature vector.
 */
export async function predictIncident(
  features: Record<string, number>,
): Promise<IncidentClassificationResponse> {
  const json = await apiFetch<any>('/api/incidents/predict', {
    method: 'POST',
    body: features,
  });
  return {
    type: json.type,
    severity: json.severity as Severity,
    confidence: json.confidence,
    incidentRiskScore: json.incident_risk_score ?? json.confidence,
    classifierVersion: json.classifier_version ?? 'xgboost-1.8-caseintel',
    featureContributions: (json.feature_contributions || []).map(mapShapContribution),
    classProbabilities: json.class_probabilities ?? {},
    extractedFeatures: json.extracted_features ?? {},
    reasoning: json.reasoning ?? '',
    baseValue: json.base_value,
    positiveContributors: (json.positive_contributors || []).map(mapShapContribution),
    negativeContributors: (json.negative_contributors || []).map(mapShapContribution),
  };
}
