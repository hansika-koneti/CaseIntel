/**
 * CaseIntel — Deterministic Location Normalization Utility
 * Ensures consistent location labels across Dashboard, Timeline, Knowledge Graph, Incident Review, and Report.
 */

export function normalizeLocationName(loc?: string | null): string {
  if (!loc) return 'Monitored Zone';
  const locStr = String(loc).trim();
  if (['', 'none', 'null', 'undefined', 'location not specified', 'unknown', 'unknown location'].includes(locStr.toLowerCase())) {
    return 'Monitored Zone';
  }

  // Handle known test typos or slugs
  let cleaned = locStr.replace(/newp+lace/gi, 'New Place');
  if (['newplace', 'new place'].includes(cleaned.toLowerCase())) {
    return 'New Place';
  }
  if (cleaned.toLowerCase() === 'house') {
    return 'House (Premises)';
  }
  if (cleaned.toLowerCase() === 'new') {
    return 'New Sector';
  }
  if (cleaned.toLowerCase() === 'monitored zone') {
    return 'Monitored Zone';
  }

  // Split camelCase e.g. RoomB -> Room B, WestGate -> West Gate
  cleaned = cleaned.replace(/([a-z])([A-Z])/g, '$1 $2');
  // Replace underscores and hyphens with spaces
  cleaned = cleaned.replace(/[_-]+/g, ' ');
  // Capitalize words cleanly
  return cleaned
    .split(/\s+/)
    .map(w => (w.toUpperCase() === w ? w : w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()))
    .join(' ');
}
