import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts';
import { TrendingUp, ChevronDown, ChevronUp } from 'lucide-react';

export interface ChartDataItem {
  feature: string;
  contribution: number;
  value: string | number;
  impactDirection?: string;
  shapValue?: number;
}

interface TooltipPayloadItem {
  value: number;
  payload: ChartDataItem;
}

const CustomTooltip = ({
  active,
  payload,
  incidentType,
}: {
  active?: boolean;
  payload?: TooltipPayloadItem[];
  incidentType?: string;
}) => {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  const isPos = p.impactDirection !== 'negative';
  const targetClass = incidentType || 'Incident Class';

  return (
    <div className="card px-3.5 py-2.5 space-y-1.5 shadow-lg border border-slate-200">
      <div className="text-[12px] font-bold" style={{ color: '#0f172a' }}>
        {p.feature}
      </div>
      <div className="text-[10px]" style={{ color: '#64748b' }}>
        Observed measurement: <span className="font-mono font-medium text-slate-900">{p.value}</span>
      </div>
      <div className="flex items-center gap-2 font-mono text-[12px]">
        <span style={{ color: isPos ? '#16a34a' : '#d97706', fontWeight: 700 }}>
          SHAP:{' '}
          {p.shapValue !== undefined
            ? p.shapValue > 0
              ? `+${p.shapValue}`
              : p.shapValue
            : `+${payload[0].value}%`}
        </span>
        <span className="text-[10px]" style={{ color: '#94a3b8' }}>
          ({p.contribution}% relative contribution)
        </span>
      </div>
      <div
        className="text-[10px] font-medium leading-tight"
        style={{ color: isPos ? '#16a34a' : '#d97706' }}
      >
        {isPos
          ? `Positive contribution: Increases probability of ${targetClass}`
          : `Negative contribution: Decreases probability of ${targetClass}`}
      </div>
    </div>
  );
};

interface TechnicalExplainabilitySectionProps {
  isOpen: boolean;
  onToggle: () => void;
  classifierVersion: string;
  baseValue?: number | string;
  incidentType: string;
  chartData: ChartDataItem[];
}

export function TechnicalExplainabilitySection({
  isOpen,
  onToggle,
  classifierVersion,
  baseValue,
  incidentType,
  chartData,
}: TechnicalExplainabilitySectionProps) {
  return (
    <div className="card overflow-hidden border border-slate-200">
      <button
        onClick={onToggle}
        className="w-full px-5 py-3.5 bg-slate-50 hover:bg-slate-100/80 transition-colors flex items-center justify-between text-left cursor-pointer border-none"
      >
        <div className="flex items-center gap-2.5">
          <div className="w-6 h-6 rounded flex items-center justify-center bg-blue-100 text-blue-700">
            <TrendingUp size={13} />
          </div>
          <div>
            <div className="text-[13px] font-bold text-slate-900">
              Technical Model Output & TreeSHAP Explainability
            </div>
            <div className="text-[11px] text-slate-500">
              Low-level XGBoost weights, base expected value, and exact SHAP vectors (for ML audit)
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-medium text-slate-500">
            {isOpen ? 'Collapse' : 'Expand Technical Details'}
          </span>
          {isOpen ? (
            <ChevronUp size={16} className="text-slate-500" />
          ) : (
            <ChevronDown size={16} className="text-slate-500" />
          )}
        </div>
      </button>

      {isOpen && (
        <div className="p-5 space-y-6 border-t border-slate-200 bg-white animate-fade-in">
          {/* Technical Metadata Row */}
          <div className="grid grid-cols-3 gap-4">
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-center">
              <div className="text-[10px] text-slate-500 uppercase font-semibold">Classifier Engine</div>
              <div className="text-[12px] font-mono font-bold text-slate-800 mt-0.5">
                {classifierVersion}
              </div>
            </div>
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-center">
              <div className="text-[10px] text-slate-500 uppercase font-semibold">Base Expected Value E[f(x)]</div>
              <div className="text-[12px] font-mono font-bold text-blue-600 mt-0.5">
                {baseValue ?? '-0.7798'}
              </div>
            </div>
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-center">
              <div className="text-[10px] text-slate-500 uppercase font-semibold">Features Analyzed</div>
              <div className="text-[12px] font-mono font-bold text-slate-800 mt-0.5">
                {chartData.length} tabular parameters
              </div>
            </div>
          </div>

          {/* TreeSHAP Chart */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="text-[13px] font-bold text-slate-800">
                Factors influencing {incidentType}
              </div>
              <div className="text-[11px] font-mono text-slate-500">
                TreeSHAP Log-Odds Contributions
              </div>
            </div>

            <div style={{ width: '100%', height: 260, minHeight: 260 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} layout="vertical" margin={{ left: 0, right: 60, top: 0, bottom: 0 }}>
                  <CartesianGrid horizontal={false} stroke="#f1f5f9" />
                  <XAxis
                    type="number"
                    domain={[0, 'auto']}
                    tick={{ fill: '#94a3b8', fontSize: 10, fontFamily: 'JetBrains Mono, monospace' }}
                    tickFormatter={(v) => `${v}%`}
                    axisLine={{ stroke: '#e2e8f0' }}
                    tickLine={false}
                  />
                  <YAxis
                    type="category"
                    dataKey="feature"
                    width={260}
                    tick={{ fill: '#475569', fontSize: 11, fontFamily: 'Inter, sans-serif' }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <Tooltip
                    content={<CustomTooltip incidentType={incidentType} />}
                    cursor={{ fill: 'rgba(241,245,249,0.8)' }}
                  />
                  <Bar dataKey="contribution" radius={[0, 4, 4, 0]}>
                    {chartData.map((entry, index) => {
                      const isNegative = entry.impactDirection === 'negative';
                      const fillColor = isNegative ? '#d97706' : '#16a34a';
                      return <Cell key={`cell-${index}`} fill={fillColor} fillOpacity={0.85} />;
                    })}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Directional Attribution Legend */}
            <div className="flex flex-wrap items-center gap-5 text-[11px] pt-1">
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-2.5 rounded-xs inline-block bg-emerald-600" />
                <strong>Positive SHAP:</strong> Increases probability of {incidentType}
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-2.5 rounded-xs inline-block bg-amber-600" />
                <strong>Negative SHAP:</strong> Decreases probability of {incidentType}
              </span>
            </div>
          </div>

          {/* Exact Feature Telemetry Table */}
          <div className="space-y-2">
            <div className="text-[12px] font-bold text-slate-800">Complete Tabular Feature Telemetry</div>
            <div className="border border-slate-200 rounded-lg overflow-hidden">
              <table className="w-full text-[11px] text-left">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-600">
                  <tr>
                    <th className="py-2 px-3">Feature Name</th>
                    <th className="py-2 px-3">Observed Value</th>
                    <th className="py-2 px-3 text-right">SHAP Value (φ)</th>
                    <th className="py-2 px-3 text-right">Relative Impact</th>
                    <th className="py-2 px-3">Directional Effect</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {chartData.map((row, idx) => (
                    <tr key={idx} className="hover:bg-slate-50">
                      <td className="py-2 px-3 font-medium text-slate-800">{row.feature}</td>
                      <td className="py-2 px-3 font-mono text-slate-600">{row.value}</td>
                      <td
                        className="py-2 px-3 font-mono font-bold text-right"
                        style={{ color: row.impactDirection === 'negative' ? '#d97706' : '#16a34a' }}
                      >
                        {row.shapValue !== undefined
                          ? row.shapValue > 0
                            ? `+${row.shapValue}`
                            : row.shapValue
                          : '—'}
                      </td>
                      <td className="py-2 px-3 font-mono text-right text-slate-700">{row.contribution}%</td>
                      <td className="py-2 px-3">
                        <span
                          className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                            row.impactDirection === 'negative'
                              ? 'bg-amber-50 text-amber-700'
                              : 'bg-emerald-50 text-emerald-700'
                          }`}
                        >
                          {row.impactDirection === 'negative'
                            ? `Pulls away from ${incidentType}`
                            : `Pushes towards ${incidentType}`}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
