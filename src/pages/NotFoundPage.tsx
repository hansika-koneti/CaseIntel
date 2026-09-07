import { useNavigate } from 'react-router-dom';
import { AlertTriangle, Home } from 'lucide-react';

export default function NotFoundPage() {
  const navigate = useNavigate();
  return (
    <div className="flex-1 flex items-center justify-center h-full" style={{ background: '#f1f5f9' }}>
      <div className="text-center space-y-4">
        <div
          className="w-16 h-16 rounded-full flex items-center justify-center mx-auto"
          style={{ background: '#fee2e2', border: '1px solid #fecaca' }}
        >
          <AlertTriangle size={28} style={{ color: '#dc2626' }} />
        </div>
        <div>
          <div className="font-mono text-[11px] mb-1" style={{ color: '#94a3b8' }}>ERROR 404</div>
          <div className="text-[18px] font-bold" style={{ color: '#0f172a' }}>Page Not Found</div>
          <div className="text-[12px] mt-1" style={{ color: '#64748b' }}>
            This route does not exist in the investigation system.
          </div>
        </div>
        <button
          onClick={() => navigate('/')}
          className="btn-primary flex items-center gap-2 mx-auto"
        >
          <Home size={13} />Return to Dashboard
        </button>
      </div>
    </div>
  );
}
