import { useNavigate } from 'react-router-dom';
import { Film, Play, AlertTriangle } from 'lucide-react';
import { SeverityBadge } from '../common/StatusBadge';
import { ConfidenceRing } from '../common/ConfidenceMeter';
import type { Severity } from '../../types';

export interface VideoActivitySegment {
  start: string;
  end: string;
  start_sec?: number;
  peak_confidence?: number;
}

export interface VideoActivityAlternative {
  activity: string;
  confidence: number;
}

export interface VideoActivityRecognitionResult {
  primary_activity: string;
  confidence: number;
  severity: Severity;
  model_name?: string;
  total_clips_analyzed?: number;
  supporting_segments?: VideoActivitySegment[];
  top_alternatives?: VideoActivityAlternative[];
}

interface VideoActivityCardProps {
  varRes: VideoActivityRecognitionResult;
  incidentType: string;
  incidentConfidence: number;
}

export function VideoActivityCard({
  varRes,
  incidentType,
  incidentConfidence,
}: VideoActivityCardProps) {
  const navigate = useNavigate();

  return (
    <div className="card p-6 border border-blue-200/90 bg-gradient-to-br from-white via-blue-50/25 to-indigo-50/20 shadow-xs space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-blue-100/80 pb-3">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-blue-600 text-white flex items-center justify-center shadow-xs">
            <Film size={16} />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-[14px] font-bold text-slate-900">
                Direct Video Activity Recognition (Spatiotemporal CNN)
              </span>
              <span className="px-2 py-0.5 rounded-md text-[10px] font-mono font-semibold bg-blue-100 text-blue-800 border border-blue-200">
                R(2+1)D-18 · Trained Surveillance Head
              </span>
            </div>
            <div className="text-[11px] text-slate-500 mt-0.5">
              Spatiotemporal 16-frame clip classification · Blind to filenames/metadata · Kinetics-400 initialized
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2 self-start sm:self-auto">
          <span className="badge badge-blue text-[10px] font-semibold uppercase">
            Temporal Video Model
          </span>
          <span className="text-[10px] font-mono text-slate-400">
            {varRes.total_clips_analyzed
              ? `${varRes.total_clips_analyzed} clips evaluated`
              : 'Multi-clip spatiotemporal analysis'}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-center">
        {/* Primary Activity & Confidence Ring */}
        <div className="flex items-center gap-5 lg:border-r border-blue-100/70 pr-4">
          <div className="relative flex-shrink-0">
            <ConfidenceRing value={varRes.confidence} size={90} />
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="font-mono text-[15px] font-bold text-blue-900">{varRes.confidence}%</span>
              <span className="text-[8px] uppercase tracking-wider text-blue-600 font-semibold">Temporal</span>
            </div>
          </div>
          <div>
            <div className="text-[10px] uppercase font-bold tracking-wider text-slate-500 mb-1">
              Predicted Video Activity
            </div>
            <div className="text-[20px] font-bold text-slate-900 mb-1.5">
              {varRes.primary_activity}
            </div>
            <div className="flex items-center gap-2">
              <SeverityBadge severity={varRes.severity} />
              <span className="text-[11px] text-slate-600">
                Direct Video Confidence: <strong className="text-slate-800">{varRes.confidence}%</strong>
              </span>
            </div>
          </div>
        </div>

        {/* Supporting Segments with Direct Jump to Video */}
        <div className="space-y-2">
          <div className="text-[10px] uppercase font-bold tracking-wider text-slate-500 flex items-center justify-between">
            <span>Supporting Video Segments</span>
            <span className="font-mono text-slate-400 text-[10px]">Peak Activity Windows</span>
          </div>
          {varRes.supporting_segments && varRes.supporting_segments.length > 0 ? (
            <div className="space-y-2">
              {varRes.supporting_segments.map((seg, sIdx) => {
                const seekSec = seg.start_sec !== undefined ? seg.start_sec : 0;
                return (
                  <div
                    key={sIdx}
                    className="p-2.5 rounded-lg bg-white border border-blue-100 shadow-2xs flex items-center justify-between gap-3"
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="font-mono text-[11px] font-bold text-blue-900 px-2 py-0.5 rounded bg-blue-50 border border-blue-200/60">
                        {seg.start} – {seg.end}
                      </span>
                      <div className="text-[10px] text-slate-600 truncate">
                        {seg.peak_confidence !== undefined && (
                          <span>
                            Peak: <strong className="font-mono text-slate-800">{seg.peak_confidence}%</strong>
                          </span>
                        )}
                      </div>
                    </div>
                    <button
                      onClick={() => navigate(`/cctv-analysis/video?t=${seekSec}`)}
                      className="btn-primary text-[11px] py-1 px-2.5 flex items-center gap-1.5 flex-shrink-0 cursor-pointer shadow-xs"
                      title={`Jump to video at ${seg.start}`}
                    >
                      <Play size={10} fill="currentColor" />
                      Play Segment
                    </button>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="text-[12px] text-slate-500 p-2.5 bg-white rounded-lg border border-blue-100">
              Uniform activity distribution across video duration.
            </div>
          )}
        </div>

        {/* Top Alternative Classes */}
        <div className="space-y-2 lg:border-l border-blue-100/70 pl-4">
          <div className="text-[10px] uppercase font-bold tracking-wider text-slate-500">
            Top Model Alternatives
          </div>
          <div className="space-y-1.5">
            {(varRes.top_alternatives || []).slice(0, 3).map((alt, aIdx) => (
              <div key={aIdx} className="space-y-0.5">
                <div className="flex justify-between text-[11px]">
                  <span className="text-slate-700 font-medium truncate">{alt.activity}</span>
                  <span className="font-mono font-bold text-slate-800">{alt.confidence}%</span>
                </div>
                <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden">
                  <div
                    className="bg-blue-600 h-full rounded-full transition-all duration-500"
                    style={{ width: `${Math.min(100, Math.max(0, alt.confidence))}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
          <div className="pt-1 text-[10px] text-slate-400">
            Independent classification head trained on surveillance activity clips.
          </div>
        </div>
      </div>

      {/* Model Disagreement / Defense-in-Depth Explanation if classifications differ */}
      {varRes.primary_activity !== incidentType && (
        <div className="p-3 rounded-lg bg-amber-50/90 border border-amber-200 text-[11px] text-amber-900 flex items-start gap-2.5">
          <AlertTriangle size={15} className="text-amber-700 flex-shrink-0 mt-0.5" />
          <div>
            <strong className="font-semibold text-amber-950">
              Dual-Pipeline Analytical Divergence:
            </strong>{' '}
            The direct spatiotemporal video model classifies visual clip motion as{' '}
            <strong className="font-mono font-bold text-amber-950">
              {varRes.primary_activity} ({varRes.confidence}%)
            </strong>
            , whereas the tabular forensic classifier evaluates engineered event attributes as{' '}
            <strong className="font-mono font-bold text-amber-950">
              {incidentType} ({incidentConfidence}%)
            </strong>
            . This divergence illustrates CaseIntel's defense-in-depth: visual spatiotemporal patterns and tabular kinematic features are assessed separately to ensure forensic rigor.
          </div>
        </div>
      )}
    </div>
  );
}
