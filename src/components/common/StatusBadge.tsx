import { clsx } from 'clsx';
import type { CSSProperties } from 'react';
import type { Severity, InvestigationStatus } from '../../types';

interface StatusBadgeProps {
  status: InvestigationStatus;
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const styles: Record<string, string> = {
    under_investigation: 'badge badge-amber',
    processing:          'badge badge-blue',
    pending:             'badge badge-slate',
    closed:              'badge badge-green',
    escalated:           'badge badge-red',
  };
  const labels: Record<string, string> = {
    under_investigation: 'Under Investigation',
    processing:          'Processing',
    pending:             'Pending Review',
    closed:              'Closed',
    escalated:           'Escalated',
  };
  return (
    <span className={clsx(styles[status] || 'badge badge-slate', className)}>
      {labels[status] || status}
    </span>
  );
}

interface SeverityBadgeProps {
  severity: Severity;
  className?: string;
}

export function SeverityBadge({ severity, className }: SeverityBadgeProps) {
  const styles: Record<string, string> = {
    CRITICAL: 'badge badge-red',
    HIGH:     'badge badge-red',
    MEDIUM:   'badge badge-amber',
    LOW:      'badge badge-green',
  };
  return (
    <span className={clsx(styles[severity] || 'badge badge-slate', className)}>
      {severity}
    </span>
  );
}

interface EntityTypeBadgeProps {
  type: string;
  className?: string;
}

export function EntityTypeBadge({ type, className }: EntityTypeBadgeProps) {
  const styles: Record<string, string> = {
    person:    'badge badge-blue',
    vehicle:   'badge',
    camera:    'badge',
    location:  'badge badge-green',
    event:     'badge badge-amber',
    activity:  'badge badge-amber',
    timestamp: 'badge badge-slate',
  };
  const vehicleStyle = { background: '#ede9fe', color: '#5b21b6', borderColor: '#ddd6fe', border: '1px solid' };
  const cameraStyle  = { background: '#fce7f3', color: '#9d174d', borderColor: '#fbcfe8', border: '1px solid' };
  const objectStyle  = { background: '#ecfeff', color: '#0e7490', borderColor: '#a5f3fc', border: '1px solid' };

  if (type === 'vehicle') return (
    <span className={clsx('badge', className)} style={vehicleStyle as CSSProperties}>{type}</span>
  );
  if (type === 'camera') return (
    <span className={clsx('badge', className)} style={cameraStyle as CSSProperties}>{type}</span>
  );
  if (type === 'object' || type === 'phone') return (
    <span className={clsx('badge', className)} style={objectStyle as CSSProperties}>object</span>
  );
  return (
    <span className={clsx(styles[type] || 'badge badge-slate', className)}>{type}</span>
  );
}
