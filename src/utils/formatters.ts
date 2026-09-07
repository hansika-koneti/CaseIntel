// ============================================================
// CaseIntel — Formatting Utilities
// ============================================================

export function formatTimestamp(isoString: string): string {
  try {
    return new Date(isoString).toLocaleString('en-IN', {
      year: 'numeric',
      month: 'short',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    });
  } catch {
    return isoString;
  }
}

export function formatConfidence(value: number): string {
  return `${value.toFixed(1)}%`;
}

export function formatDuration(value: string): string {
  return value;
}

export function severityColor(severity: string): string {
  switch (severity) {
    case 'CRITICAL': return 'text-red-500';
    case 'HIGH':     return 'text-red-400';
    case 'MEDIUM':   return 'text-amber-400';
    case 'LOW':      return 'text-green-400';
    default:         return 'text-gray-400';
  }
}

export function severityBg(severity: string): string {
  switch (severity) {
    case 'CRITICAL': return 'bg-red-500/20 border-red-500/40 text-red-400';
    case 'HIGH':     return 'bg-red-400/15 border-red-400/30 text-red-400';
    case 'MEDIUM':   return 'bg-amber-400/15 border-amber-400/30 text-amber-400';
    case 'LOW':      return 'bg-green-400/15 border-green-400/30 text-green-400';
    default:         return 'bg-gray-400/10 border-gray-400/20 text-gray-400';
  }
}

export function statusColor(status: string): string {
  switch (status) {
    case 'under_investigation': return 'text-amber-400';
    case 'processing':          return 'text-cyan-400';
    case 'pending':             return 'text-gray-400';
    case 'closed':              return 'text-green-400';
    case 'escalated':           return 'text-red-400';
    default:                    return 'text-gray-400';
  }
}

export function statusBg(status: string): string {
  switch (status) {
    case 'under_investigation': return 'bg-amber-400/15 border-amber-400/30 text-amber-400';
    case 'processing':          return 'bg-cyan-400/15 border-cyan-400/30 text-cyan-400';
    case 'pending':             return 'bg-gray-400/10 border-gray-400/20 text-gray-500';
    case 'closed':              return 'bg-green-400/15 border-green-400/30 text-green-400';
    case 'escalated':           return 'bg-red-400/15 border-red-400/30 text-red-400';
    default:                    return 'bg-gray-400/10 border-gray-400/20 text-gray-400';
  }
}

export function statusLabel(status: string): string {
  switch (status) {
    case 'under_investigation': return 'Under Investigation';
    case 'processing':          return 'Processing';
    case 'pending':             return 'Pending Review';
    case 'closed':              return 'Closed';
    case 'escalated':           return 'Escalated';
    default:                    return status;
  }
}

export function entityTypeColor(type: string): string {
  switch (type) {
    case 'person':    return 'text-cyan-400 bg-cyan-400/10 border-cyan-400/30';
    case 'vehicle':   return 'text-blue-400 bg-blue-400/10 border-blue-400/30';
    case 'camera':    return 'text-purple-400 bg-purple-400/10 border-purple-400/30';
    case 'location':  return 'text-green-400 bg-green-400/10 border-green-400/30';
    case 'event':     return 'text-amber-400 bg-amber-400/10 border-amber-400/30';
    case 'activity':  return 'text-orange-400 bg-orange-400/10 border-orange-400/30';
    case 'timestamp': return 'text-gray-400 bg-gray-400/10 border-gray-400/30';
    default:          return 'text-gray-400 bg-gray-400/10 border-gray-400/30';
  }
}

export function entityTypeLabel(type: string): string {
  return type.charAt(0).toUpperCase() + type.slice(1);
}

export function pipelineStageStatusIcon(status: string): string {
  switch (status) {
    case 'completed':  return '✓';
    case 'processing': return '⟳';
    case 'error':      return '✗';
    default:           return '○';
  }
}

export function confidenceLevel(value: number): 'high' | 'medium' | 'low' {
  if (value >= 85) return 'high';
  if (value >= 65) return 'medium';
  return 'low';
}

export function confidenceLevelColor(value: number): string {
  const level = confidenceLevel(value);
  if (level === 'high')   return 'text-green-400';
  if (level === 'medium') return 'text-amber-400';
  return 'text-red-400';
}

export function confidenceLevelBg(value: number): string {
  const level = confidenceLevel(value);
  if (level === 'high')   return 'bg-green-400';
  if (level === 'medium') return 'bg-amber-400';
  return 'bg-red-400';
}

export { normalizeLocationName } from './location';

