import { confidenceLevel, formatConfidence } from '../../utils/formatters';

interface ConfidenceMeterProps {
  value: number;
  showLabel?: boolean;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function ConfidenceMeter({ value, showLabel = true, size = 'md', className }: ConfidenceMeterProps) {
  const level = confidenceLevel(value);
  const fillClass = level === 'high' ? 'conf-high' : level === 'medium' ? 'conf-medium' : 'conf-low';
  const textColor = level === 'high' ? '#16a34a' : level === 'medium' ? '#d97706' : '#dc2626';
  const heightPx = size === 'sm' ? 4 : size === 'lg' ? 10 : 6;

  return (
    <div className={className} style={{ width: '100%' }}>
      {showLabel && (
        <div className="flex justify-between items-center mb-1">
          <span className="section-label">Confidence</span>
          <span className="font-mono text-[12px] font-semibold" style={{ color: textColor }}>
            {formatConfidence(value)}
          </span>
        </div>
      )}
      <div className="conf-track" style={{ height: heightPx }}>
        <div className={`conf-fill ${fillClass}`} style={{ width: `${Math.min(value, 100)}%` }} />
      </div>
    </div>
  );
}

interface ConfidenceRingProps {
  value: number;
  size?: number;
}

export function ConfidenceRing({ value, size = 80 }: ConfidenceRingProps) {
  const radius = (size - 8) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (value / 100) * circumference;

  const level = confidenceLevel(value);
  const color = level === 'high' ? '#16a34a' : level === 'medium' ? '#d97706' : '#dc2626';
  const trackColor = '#e2e8f0';

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="rotate-[-90deg]">
      <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke={trackColor} strokeWidth="5" />
      <circle
        cx={size / 2} cy={size / 2} r={radius}
        fill="none" stroke={color} strokeWidth="5"
        strokeLinecap="round"
        strokeDasharray={circumference}
        strokeDashoffset={strokeDashoffset}
        style={{ transition: 'stroke-dashoffset 1s ease' }}
      />
    </svg>
  );
}
