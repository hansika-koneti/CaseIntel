import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { Play, Pause, SkipBack, SkipForward, Maximize2, AlertTriangle, User, Car, Smartphone, Camera, Loader2, Video as VideoIcon } from 'lucide-react';
import { getInvestigation, setActiveVideo } from '../api/investigations';
import { getVideoInfo } from '../api/videos';
import type { Investigation, Entity } from '../types';
import { EntityTypeBadge } from '../components/common/StatusBadge';
import { ConfidenceMeter } from '../components/common/ConfidenceMeter';
import { normalizeLocationName } from '../utils/location';

function parseTimestampToSeconds(ts: string): number {
  if (!ts) return 0;
  if (ts.includes(':')) {
    const parts = ts.split(':').map(Number);
    if (parts.length === 2 && !isNaN(parts[0]) && !isNaN(parts[1])) {
      return parts[0] * 60 + parts[1];
    }
    if (parts.length === 3 && !isNaN(parts[0]) && !isNaN(parts[1]) && !isNaN(parts[2])) {
      return parts[0] * 3600 + parts[1] * 60 + parts[2];
    }
  }
  const parsed = Date.parse(ts);
  if (!isNaN(parsed)) {
    return Math.floor(parsed / 1000);
  }
  return 0;
}

export default function VideoAnalysisPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [playing, setPlaying] = useState(false);
  const [currentTimeFormatted, setCurrentTimeFormatted] = useState('00:00');
  const [currentTimeSec, setCurrentTimeSec] = useState(0);
  const [durationSec, setDurationSec] = useState(0);
  const [selectedEvent, setSelectedEvent] = useState<string | null>(null);
  const [selectedEntity, setSelectedEntity] = useState<string>('');

  const [inv, setInv] = useState<Investigation | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const videoRef = useRef<HTMLVideoElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [videoBox, setVideoBox] = useState<{ left: number; top: number; width: number; height: number } | null>(null);

  const calcVideoBox = useCallback(() => {
    const vid = videoRef.current;
    const cnt = containerRef.current;
    if (!vid || !cnt) return;
    const cW = cnt.clientWidth;
    const cH = cnt.clientHeight;
    const vW = vid.videoWidth || 16;
    const vH = vid.videoHeight || 9;
    if (!cW || !cH || !vW || !vH) return;

    const cRatio = cW / cH;
    const vRatio = vW / vH;

    let rW: number;
    let rH: number;
    let rLeft: number;
    let rTop: number;

    if (vRatio > cRatio) {
      rW = cW;
      rH = cW / vRatio;
      rLeft = 0;
      rTop = (cH - rH) / 2;
    } else {
      rH = cH;
      rW = cH * vRatio;
      rLeft = (cW - rW) / 2;
      rTop = 0;
    }

    setVideoBox({ left: rLeft, top: rTop, width: rW, height: rH });
  }, []);

  useEffect(() => {
    calcVideoBox();
    window.addEventListener('resize', calcVideoBox);
    return () => window.removeEventListener('resize', calcVideoBox);
  }, [calcVideoBox]);

  useEffect(() => {
    let mounted = true;
    const loadCase = async () => {
      let activeId = localStorage.getItem('caseintel-active-case-id');
      const urlVid = searchParams.get('video_id');

      // If video_id in URL is specified, ensure we load its parent investigation
      if (urlVid) {
        try {
          const vInfo = await getVideoInfo(urlVid);
          if (vInfo && vInfo.investigationId && vInfo.investigationId !== activeId) {
            activeId = vInfo.investigationId;
            localStorage.setItem('caseintel-active-case-id', activeId);
            window.dispatchEvent(new Event('active-case-changed'));
          }
        } catch {
          // ignore lookup error
        }
      }

      if (!activeId) {
        if (mounted) {
          setInv(null);
          setLoading(false);
          setError(null);
        }
        return;
      }
      setLoading(true);
      setError(null);
      getInvestigation(activeId)
        .then(data => {
          if (!mounted) return;
          setInv(data);
          if (data.entities.length > 0) {
            const first = data.entities.find(e => ['person', 'vehicle'].includes(e.type)) || data.entities[0];
            if (first) setSelectedEntity(first.id);
          }
          if (data.events.length > 0) {
            setCurrentTimeFormatted(data.events[0].timestamp);
            setCurrentTimeSec(parseTimestampToSeconds(data.events[0].timestamp));
          }
        })
        .catch(err => {
          if (!mounted) return;
          setError(err instanceof Error ? err.message : 'Failed to load investigation');
        })
        .finally(() => { if (mounted) setLoading(false); });
    };

    loadCase();
    window.addEventListener('active-case-changed', loadCase);
    return () => { mounted = false; window.removeEventListener('active-case-changed', loadCase); };
  }, [searchParams]);

  // 60 FPS requestAnimationFrame loop for continuous, smooth bounding box updates
  useEffect(() => {
    if (!playing) return;
    let animId: number;
    const tick = () => {
      if (videoRef.current) {
        const cur = videoRef.current.currentTime;
        setCurrentTimeSec(cur);
        const h = Math.floor(cur / 3600);
        const m = Math.floor((cur % 3600) / 60);
        const s = Math.floor(cur % 60);
        const formatted = (durationSec >= 3600 || h > 0)
          ? `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
          : `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
        setCurrentTimeFormatted(formatted);
      }
      animId = requestAnimationFrame(tick);
    };
    animId = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(animId);
  }, [playing]);

  // Pre-sort and index trajectories once per entity list update rather than on every 60 FPS animation frame
  // Positioned at the top level with all React hooks to strictly adhere to React Rules of Hooks
  const entityTrajectories = useMemo(() => {
    if (!inv?.entities) return new Map<string, Array<any>>();
    const map = new Map<string, Array<any>>();
    for (const e of inv.entities) {
      const traj = e.trajectory || [];
      if (traj.length > 0) {
        const sorted = [...traj].map(pt => ({
          ...pt,
          t: (pt as any).timestampSec ?? (pt as any).timestamp_sec ?? (pt.frame / 25),
        })).sort((a, b) => a.t - b.t);
        map.set(e.id, sorted);
      }
    }
    return map;
  }, [inv?.entities]);

  const API_BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://127.0.0.1:8000';
  const urlVideoId = searchParams.get('video_id');
  const availableVideos = inv?.videos || [];

  // Deterministic active video resolution:
  // 1. URL search param ?video_id=... (if valid)
  // 2. Investigation activeVideoId from backend
  // 3. Investigation videoId from backend
  // 4. Stored active video ID in localStorage (if valid)
  // 5. Most recent video in inv.videos[0]
  let activeVideoId: string | null = null;
  if (urlVideoId && availableVideos.some(v => v.id === urlVideoId)) {
    activeVideoId = urlVideoId;
  } else if (inv?.activeVideoId && availableVideos.some(v => v.id === inv.activeVideoId)) {
    activeVideoId = inv.activeVideoId;
  } else if (inv?.videoId && availableVideos.some(v => v.id === inv.videoId)) {
    activeVideoId = inv.videoId;
  } else {
    const stored = localStorage.getItem('caseintel-active-video-id');
    if (stored && availableVideos.some(v => v.id === stored)) {
      activeVideoId = stored;
    } else if (availableVideos.length > 0) {
      activeVideoId = availableVideos[0].id;
    }
  }

  // Synchronize localStorage in an effect to avoid render side effects
  useEffect(() => {
    if (activeVideoId && localStorage.getItem('caseintel-active-video-id') !== activeVideoId) {
      localStorage.setItem('caseintel-active-video-id', activeVideoId);
    }
  }, [activeVideoId]);

  const [ocrInfo, setOcrInfo] = useState<{ detected: boolean; status: string; timestamp?: string | null; engine?: string } | null>(null);

  useEffect(() => {
    if (!activeVideoId) {
      setOcrInfo(null);
      return;
    }
    let mounted = true;
    fetch(`${API_BASE}/api/videos/${activeVideoId}/ocr`)
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (mounted && data) setOcrInfo(data);
      })
      .catch(() => {
        if (mounted) setOcrInfo(null);
      });
    return () => { mounted = false; };
  }, [activeVideoId, API_BASE]);

  const togglePlay = () => {
    if (!videoRef.current) return;
    if (playing) {
      videoRef.current.pause();
      setPlaying(false);
    } else {
      videoRef.current.play().then(() => setPlaying(true)).catch(() => {});
    }
  };

  const handleSeek = (timeInSec: number) => {
    if (videoRef.current) {
      videoRef.current.currentTime = timeInSec;
      setCurrentTimeSec(timeInSec);
      const m = Math.floor(timeInSec / 60);
      const s = Math.floor(timeInSec % 60);
      setCurrentTimeFormatted(`${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`);
    }
  };

  if (loading && !inv) {
    return (
      <div className="p-12 flex items-center justify-center gap-3" style={{ color: '#64748b' }}>
        <Loader2 size={20} className="animate-spin text-blue-600" />
        <span className="text-[13px]">Loading video forensic analysis…</span>
      </div>
    );
  }

  if (error && !inv) {
    return (
      <div className="p-12 max-w-md mx-auto text-center space-y-3">
        <AlertTriangle size={32} className="mx-auto text-red-500" />
        <div className="text-[14px] font-semibold text-slate-800">Unable to load investigation</div>
        <div className="text-[12px] text-slate-500">{error}</div>
        <button onClick={() => window.location.reload()} className="btn-primary">Retry</button>
      </div>
    );
  }

  // Explicit empty state if no active investigation exists
  if (!inv) {
    return (
      <div className="p-6 space-y-5" style={{ maxWidth: 1600 }}>
        <div>
          <div className="section-label mb-1 flex items-center gap-2">
            <VideoIcon size={12} />
            <span>Forensic Video Stream</span>
          </div>
          <h1 className="text-[22px] font-bold" style={{ color: '#0f172a' }}>Video Viewer</h1>
        </div>

        <div className="card p-12 text-center space-y-4 max-w-xl mx-auto my-12" style={{ border: '1px dashed #cbd5e1' }}>
          <div className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto" style={{ background: '#f1f5f9', color: '#64748b' }}>
            <VideoIcon size={32} />
          </div>
          <div>
            <h2 className="text-[18px] font-bold" style={{ color: '#0f172a' }}>No video uploaded</h2>
            <p className="text-[13px] mt-1.5 leading-relaxed" style={{ color: '#64748b' }}>
              Upload a CCTV video to begin analysis.
            </p>
          </div>
          <div className="pt-2">
            <button onClick={() => navigate('/cctv-analysis')} className="btn-primary flex items-center gap-2 mx-auto">
              <VideoIcon size={14} />
              Go to CCTV Analysis
            </button>
          </div>
        </div>
      </div>
    );
  }

  const currentVideoObj = availableVideos.find(v => v.id === activeVideoId) || (availableVideos.length > 0 ? availableVideos[0] : null);

  // Explicit empty state if investigation has no uploaded videos
  if (availableVideos.length === 0 || !activeVideoId || !currentVideoObj) {
    return (
      <div className="p-6 space-y-5" style={{ maxWidth: 1600 }}>
        <div className="flex items-center justify-between">
          <div>
            <div className="section-label mb-1 flex items-center gap-2">
              <VideoIcon size={12} />
              <span>Forensic Video Stream</span>
            </div>
            <h1 className="text-[22px] font-bold" style={{ color: '#0f172a' }}>Video Viewer</h1>
            <div className="text-[12px] mt-0.5" style={{ color: '#94a3b8' }}>
              {inv.caseNumber} — {normalizeLocationName(inv.location)}
            </div>
          </div>
          <button onClick={() => navigate('/cctv-analysis')} className="btn-primary flex items-center gap-2">
            <VideoIcon size={13} />
            <span>Upload Video</span>
          </button>
        </div>

        <div className="card p-12 text-center space-y-4 max-w-xl mx-auto my-12" style={{ border: '1px dashed #cbd5e1' }}>
          <div className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto" style={{ background: '#f1f5f9', color: '#64748b' }}>
            <VideoIcon size={32} />
          </div>
          <div>
            <h2 className="text-[18px] font-bold" style={{ color: '#0f172a' }}>No video uploaded</h2>
            <p className="text-[13px] mt-1.5 leading-relaxed" style={{ color: '#64748b' }}>
              Upload a CCTV video to begin analysis.
            </p>
          </div>
          <div className="pt-2">
            <button onClick={() => navigate('/cctv-analysis')} className="btn-primary flex items-center gap-2 mx-auto">
              <VideoIcon size={14} />
              Go to CCTV Analysis
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Explicit state if video is uploaded but analysis has not been executed yet
  if (currentVideoObj.status === 'uploaded' && inv.videoCount === 0 && (!inv.events || inv.events.length === 0)) {
    return (
      <div className="p-6 space-y-5" style={{ maxWidth: 1600 }}>
        <div className="flex items-center justify-between">
          <div>
            <div className="section-label mb-1 flex items-center gap-2">
              <VideoIcon size={12} />
              <span>Forensic Video Stream</span>
            </div>
            <h1 className="text-[22px] font-bold" style={{ color: '#0f172a' }}>Video Analysis Pending</h1>
            <div className="text-[12px] mt-0.5" style={{ color: '#94a3b8' }}>
              {inv.caseNumber} — {currentVideoObj.filename}
            </div>
          </div>
          <button onClick={() => navigate('/cctv-analysis')} className="btn-primary flex items-center gap-2">
            <VideoIcon size={13} />
            <span>Go to CCTV Analysis</span>
          </button>
        </div>

        <div className="card p-12 text-center space-y-4 max-w-xl mx-auto my-12" style={{ border: '1px solid #bfdbfe', background: '#f8fafc' }}>
          <div className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto" style={{ background: '#eff6ff', color: '#2563eb' }}>
            <Loader2 size={32} className="animate-spin" />
          </div>
          <div>
            <h2 className="text-[18px] font-bold" style={{ color: '#0f172a' }}>Video Uploaded — Analysis Pending</h2>
            <p className="text-[13px] mt-1.5 leading-relaxed" style={{ color: '#64748b' }}>
              Video footage is saved but the detection and behavioral event extraction pipeline has not been executed yet.
            </p>
          </div>
          <div className="pt-2">
            <button onClick={() => navigate('/cctv-analysis')} className="btn-primary flex items-center gap-2 mx-auto">
              Run Pipeline on CCTV Analysis Page
            </button>
          </div>
        </div>
      </div>
    );
  }

  const videoStreamUrl = activeVideoId ? `${API_BASE}/api/videos/${activeVideoId}/stream` : null;
  const camId = currentVideoObj?.cameraId || (currentVideoObj as any)?.camera_id || (inv.cameraIds && inv.cameraIds[0]) || 'C-01';
  const suspiciousEvents = inv.events.filter(e => e.isSuspicious);
  const firstSuspicious = suspiciousEvents[0];

  const entity = inv.entities.find(e => e.id === selectedEntity);

  const relevantEvents = inv.events.filter(e => !e.videoId || !activeVideoId || e.videoId === activeVideoId);
  const displayEvents = relevantEvents.length > 0 ? relevantEvents : inv.events;

  const TIMELINE_EVENTS = displayEvents.map((e, i, arr) => ({
    ...e,
    timeSec: parseTimestampToSeconds(e.timestamp),
    xPercent: arr.length > 1 ? 5 + (i * 90) / (arr.length - 1) : 50,
  }));

  const handleSwitchVideo = async (newVidId: string) => {
    if (!inv || newVidId === activeVideoId) return;
    setSearchParams({ video_id: newVidId });
    localStorage.setItem('caseintel-active-video-id', newVidId);
    try {
      await setActiveVideo(inv.id, newVidId);
      const freshInv = await getInvestigation(inv.id);
      setInv(freshInv);
    } catch (err) {
      console.error('Failed to set active video:', err);
    }
  };

  // Dynamic entity position based on video current time and real ByteTrack trajectory.
  // Entities are scoped to the active video to prevent leakage between different uploaded videos.
  const detections = inv.entities
    .filter(e => (!e.videoId || !activeVideoId || e.videoId === activeVideoId) && ['person', 'vehicle', 'car', 'truck', 'object', 'baggage'].includes(e.type))
    .map((e: Entity) => {
      let isVisible = false;
      let left = 0;
      let top = 0;
      let w = 0;
      let h = 0;

      const sorted = entityTrajectories.get(e.id);
      if (sorted && sorted.length > 0) {
        // Fast binary search to find points bracketing currentTimeSec in O(log N)
        let low = 0;
        let high = sorted.length - 1;
        let prevPt = sorted[0];
        let nextPt = sorted[sorted.length - 1];

        while (low <= high) {
          const mid = Math.floor((low + high) / 2);
          if (sorted[mid].t <= currentTimeSec) {
            prevPt = sorted[mid];
            low = mid + 1;
          } else {
            nextPt = sorted[mid];
            high = mid - 1;
          }
        }

        const closest = Math.abs(prevPt.t - currentTimeSec) <= Math.abs(nextPt.t - currentTimeSec) ? prevPt : nextPt;
        const timeDiff = Math.abs(closest.t - currentTimeSec);

        // Hide bounding box if no detection within 0.6s
        if (timeDiff <= 0.6) {
          isVisible = true;
          const span = nextPt.t - prevPt.t;

          if (span > 0.001 && span <= 0.8 && currentTimeSec >= prevPt.t && currentTimeSec <= nextPt.t) {
            const alpha = (currentTimeSec - prevPt.t) / span;
            const pW = (prevPt as any).w ?? 14;
            const nW = (nextPt as any).w ?? 14;
            const pH = (prevPt as any).h ?? 32;
            const nH = (nextPt as any).h ?? 32;
            w = pW + (nW - pW) * alpha;
            h = pH + (nH - pH) * alpha;

            const pX = (prevPt as any).x !== undefined && (prevPt as any).w !== undefined
              ? (prevPt as any).x
              : ((prevPt as any).center_x ?? (prevPt as any).x ?? 50) - pW / 2;
            const nX = (nextPt as any).x !== undefined && (nextPt as any).w !== undefined
              ? (nextPt as any).x
              : ((nextPt as any).center_x ?? (nextPt as any).x ?? 50) - nW / 2;
            const pY = (prevPt as any).y !== undefined && (prevPt as any).h !== undefined
              ? (prevPt as any).y
              : ((prevPt as any).center_y ?? (prevPt as any).y ?? 50) - pH / 2;
            const nY = (nextPt as any).y !== undefined && (nextPt as any).h !== undefined
              ? (nextPt as any).y
              : ((nextPt as any).center_y ?? (nextPt as any).y ?? 50) - nH / 2;

            left = pX + (nX - pX) * alpha;
            top = pY + (nY - pY) * alpha;
          } else {
            w = (closest as any).w ?? 14;
            h = (closest as any).h ?? 32;
            left = (closest as any).x !== undefined && (closest as any).w !== undefined
              ? (closest as any).x
              : ((closest as any).center_x ?? (closest as any).x ?? 50) - w / 2;
            top = (closest as any).y !== undefined && (closest as any).h !== undefined
              ? (closest as any).y
              : ((closest as any).center_y ?? (closest as any).y ?? 50) - h / 2;
          }
        }
      }

      return {
        id: e.id,
        type: e.type,
        label: e.id,
        conf: e.confidence,
        left: Math.max(0, Math.min(100 - w, left)),
        top: Math.max(0, Math.min(100 - h, top)),
        w: Math.max(2, Math.min(100, w)),
        h: Math.max(2, Math.min(100, h)),
        isVisible,
        color: e.type === 'person' ? '#2563eb' : '#7c3aed',
        textColor: e.type === 'person' ? '#60a5fa' : '#c084fc',
      };
    });

  return (
    <div className="p-6 space-y-5" style={{ maxWidth: 1600 }}>
      {/* Header with Camera/Feed Selector */}
      <div className="flex items-center justify-between">
        <div>
          <div className="section-label mb-1 flex items-center gap-2">
            <VideoIcon size={12} />
            <span>Forensic Video Stream</span>
          </div>
          <h1 className="text-[22px] font-bold" style={{ color: '#0f172a' }}>
            {camId} — {normalizeLocationName(currentVideoObj?.location || inv.location)}
          </h1>
          <div className="font-mono text-[11px] mt-0.5 flex items-center gap-2 flex-wrap" style={{ color: '#94a3b8' }}>
            <span>{inv.caseNumber}</span>
            <span>·</span>
            <span className="font-semibold text-slate-700">{currentVideoObj?.filename || 'video.mp4'}</span>
            <span>·</span>
            <span>Duration: {durationSec > 0 ? `${Math.round(durationSec)}s` : (inv.durationAnalyzed || '00:00:00')}</span>
            <span>·</span>
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-mono bg-slate-100 border border-slate-200 text-slate-700">
              <span className="font-bold text-slate-600">EasyOCR:</span>
              {ocrInfo ? (
                ocrInfo.detected ? (
                  <span className="text-emerald-700 font-bold">{ocrInfo.timestamp}</span>
                ) : (
                  <span className="text-slate-500">{ocrInfo.status}</span>
                )
              ) : (
                <span className="text-slate-400">Inspecting OSD...</span>
              )}
            </span>
          </div>
        </div>

        {/* Camera / Video Feed Dropdown if multiple feeds exist */}
        {availableVideos.length > 1 && (
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-medium" style={{ color: '#64748b' }}>Camera Feed:</span>
            <select
              value={activeVideoId || ''}
              onChange={(e) => handleSwitchVideo(e.target.value)}
              className="px-3 py-1.5 rounded text-[12px] font-medium border border-slate-300 bg-white text-slate-800 shadow-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              {availableVideos.map((v) => (
                <option key={v.id} value={v.id}>
                  {(v.cameraId || (v as any).camera_id || 'C-01')} — {v.filename}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      <div className="grid grid-cols-3 gap-5">
        {/* Video Player */}
        <div className="col-span-2 space-y-4">
          <div className="card overflow-hidden">
            {/* Video Frame Container */}
            <div ref={containerRef} className="relative aspect-video overflow-hidden" style={{ background: '#0b1120' }}>
              {videoStreamUrl ? (
                <video
                  key={activeVideoId || 'default'}
                  ref={videoRef}
                  src={videoStreamUrl}
                  className="absolute inset-0 w-full h-full object-contain"
                  controls={false}
                  playsInline
                  loop
                  muted
                  onLoadedMetadata={(e) => {
                    const dur = (e.target as HTMLVideoElement).duration;
                    if (!isNaN(dur)) setDurationSec(dur);
                    calcVideoBox();
                  }}
                  onTimeUpdate={(e) => {
                    const t = (e.target as HTMLVideoElement).currentTime;
                    setCurrentTimeSec(t);
                    const m = Math.floor(t / 60);
                    const s = Math.floor(t % 60);
                    setCurrentTimeFormatted(`${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`);
                  }}
                  onPlay={() => setPlaying(true)}
                  onPause={() => setPlaying(false)}
                />
              ) : (
                <div className="absolute inset-0 flex flex-col items-center justify-center text-slate-500 gap-2">
                  <VideoIcon size={36} className="text-slate-600" />
                  <div className="font-mono text-[12px]">No live video stream connected</div>
                </div>
              )}

              {/* Real Detection Boxes Overlay — Positioned inside exact rendered video box */}
              {videoBox && (
                <div
                  className="absolute pointer-events-none"
                  style={{
                    left: `${videoBox.left}px`,
                    top: `${videoBox.top}px`,
                    width: `${videoBox.width}px`,
                    height: `${videoBox.height}px`,
                  }}
                >
                  {detections.filter(det => det.isVisible).map(det => (
                    <div
                      key={det.id}
                      onClick={() => setSelectedEntity(det.id)}
                      className="absolute cursor-pointer pointer-events-auto transition-all duration-75"
                      style={{
                        left: `${det.left}%`,
                        top: `${det.top}%`,
                        width: `${det.w}%`,
                        height: `${det.h}%`,
                        border: `2px solid ${det.color}`,
                        background: `${det.color}15`,
                        borderRadius: 3,
                        boxShadow: `0 0 0 1px ${det.color}40`,
                      }}
                    >
                      <div
                        className="absolute -top-5 left-0 font-mono text-[10px] px-1.5 py-0.5 whitespace-nowrap rounded-t font-semibold"
                        style={{ background: 'rgba(15,23,42,0.92)', color: det.textColor, border: `1px solid ${det.color}40` }}
                      >
                        {det.label} · {det.conf}%
                      </div>
                      {/* Corner notches */}
                      <div className="absolute top-0 left-0 w-2 h-2" style={{ borderTop: `2px solid ${det.color}`, borderLeft: `2px solid ${det.color}` }} />
                      <div className="absolute top-0 right-0 w-2 h-2" style={{ borderTop: `2px solid ${det.color}`, borderRight: `2px solid ${det.color}` }} />
                      <div className="absolute bottom-0 left-0 w-2 h-2" style={{ borderBottom: `2px solid ${det.color}`, borderLeft: `2px solid ${det.color}` }} />
                      <div className="absolute bottom-0 right-0 w-2 h-2" style={{ borderBottom: `2px solid ${det.color}`, borderRight: `2px solid ${det.color}` }} />
                    </div>
                  ))}
                </div>
              )}

              {/* HUD overlays */}
              <div
                className="absolute top-2 left-2 font-mono text-[10px] px-2 py-1 rounded flex items-center gap-1.5"
                style={{ background: 'rgba(15,23,42,0.85)', color: '#4ade80' }}
              >
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                STREAM &nbsp; {currentTimeFormatted} &nbsp; {camId}
              </div>

              <div
                className="absolute top-2 right-2 font-mono text-[10px] px-2 py-1 rounded"
                style={{ background: 'rgba(15,23,42,0.85)', color: '#94a3b8' }}
              >

                {inv.durationAnalyzed ? `Duration: ${inv.durationAnalyzed}` : 'Forensic Track'}
              </div>

              {/* Suspicious banner */}
              {firstSuspicious && (
                <div
                  className="absolute bottom-2 left-2 right-2 rounded px-3 py-1.5 flex items-center gap-2"
                  style={{ background: 'rgba(239,68,68,0.15)', border: '1px solid rgba(239,68,68,0.4)', backdropFilter: 'blur(4px)' }}
                >
                  <AlertTriangle size={11} style={{ color: '#dc2626', flexShrink: 0 }} />
                  <span className="text-[11px] font-medium" style={{ color: '#fca5a5' }}>
                    {firstSuspicious.description || `Suspicious activity flagged at ${firstSuspicious.timestamp}`}
                  </span>
                </div>
              )}

              {/* Play overlay if paused */}
              {!playing && (
                <div
                  className="absolute inset-0 flex items-center justify-center cursor-pointer bg-black/20"
                  onClick={togglePlay}
                >
                  <div
                    className="w-14 h-14 rounded-full flex items-center justify-center hover:scale-105 transition-transform"
                    style={{ background: 'rgba(255,255,255,0.2)', border: '1px solid rgba(255,255,255,0.35)' }}
                  >
                    <Play size={20} className="text-white ml-1" />
                  </div>
                </div>
              )}
            </div>

            {/* Controls */}
            <div className="p-3" style={{ background: '#f8fafc', borderTop: '1px solid #e2e8f0' }}>
              <div className="flex items-center gap-3 mb-2">
                <button
                  style={{ color: '#64748b' }}
                  title="Rewind to start"
                  onClick={() => handleSeek(0)}
                >
                  <SkipBack size={14} />
                </button>
                <button
                  className="w-7 h-7 rounded-md flex items-center justify-center shadow-sm"
                  style={{ background: '#2563eb', border: 'none' }}
                  onClick={togglePlay}
                >
                  {playing ? <Pause size={12} className="text-white" /> : <Play size={12} className="text-white ml-0.5" />}
                </button>
                <button
                  style={{ color: '#64748b' }}
                  title="Forward to first event"
                  onClick={() => {
                    if (TIMELINE_EVENTS.length > 0) handleSeek(TIMELINE_EVENTS[0].timeSec);
                  }}
                >
                  <SkipForward size={14} />
                </button>
                <div className="font-mono text-[11px] font-semibold" style={{ color: '#334155' }}>
                  {currentTimeFormatted} / {durationSec > 0 ? `${Math.floor(durationSec / 60).toString().padStart(2, '0')}:${Math.floor(durationSec % 60).toString().padStart(2, '0')}` : (inv.durationAnalyzed || '00:00')}
                </div>
                <div className="flex-1" />
                <button
                  style={{ color: '#64748b' }}
                  title="Fullscreen"
                  onClick={() => {
                    if (videoRef.current?.requestFullscreen) videoRef.current.requestFullscreen();
                  }}
                >
                  <Maximize2 size={14} />
                </button>
              </div>

              {/* Interactive Timeline scrubber */}
              <div
                className="relative h-8 cursor-pointer group"
                onClick={(e) => {
                  const rect = e.currentTarget.getBoundingClientRect();
                  const pct = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
                  const dur = durationSec > 0 ? durationSec : (parseTimestampToSeconds(inv.durationAnalyzed) || 1);
                  handleSeek(pct * dur);
                }}
              >
                <div className="absolute inset-x-0 top-3" style={{ height: 6, background: '#e2e8f0', borderRadius: 3 }}>
                  <div
                    style={{
                      position: 'absolute',
                      left: 0,
                      height: '100%',
                      width: `${durationSec > 0 ? (currentTimeSec / durationSec) * 100 : (parseTimestampToSeconds(inv.durationAnalyzed) > 0 ? (currentTimeSec / parseTimestampToSeconds(inv.durationAnalyzed)) * 100 : 0)}%`,
                      background: '#3b82f6',
                      borderRadius: 3,
                    }}
                  />
                </div>

                {/* Event Markers on timeline */}
                {TIMELINE_EVENTS.map(evt => (
                  <div
                    key={evt.id}
                    className="absolute top-0 -translate-x-1/2 cursor-pointer group/dot"
                    style={{ left: `${evt.xPercent}%` }}
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedEvent(evt.id);
                      handleSeek(evt.timeSec);
                    }}
                  >
                    <div
                      className="w-2.5 h-2.5 rounded-full mt-2 group-hover/dot:scale-125 transition-transform"
                      style={{
                        background: evt.isSuspicious ? '#dc2626' : '#2563eb',
                        transform: selectedEvent === evt.id ? 'scale(1.3)' : 'none',
                        boxShadow: selectedEvent === evt.id ? '0 0 0 2px rgba(37,99,235,0.4)' : 'none',
                      }}
                    />
                    <div
                      className="absolute -top-5 left-1/2 -translate-x-1/2 rounded px-1.5 py-0.5 font-mono text-[9px] whitespace-nowrap opacity-0 group-hover/dot:opacity-100 transition-opacity pointer-events-none z-10"
                      style={{ background: '#0f172a', border: '1px solid #334155', color: '#f8fafc' }}
                    >
                      {evt.timestamp} · {evt.action}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Entity Panel */}
        <div className="space-y-4">
          {/* Detected Entities */}
          <div className="card p-4">
            <div className="section-label mb-3">
              Detected Entities ({inv.entities.filter(e => ['person', 'vehicle', 'car', 'truck', 'object', 'phone'].includes(e.type)).length})
            </div>
            {inv.entities.filter(e => ['person', 'vehicle', 'car', 'truck', 'object', 'phone'].includes(e.type)).length === 0 ? (
              <div className="text-[12px] text-slate-500 py-3 text-center">No entities detected in this video feed.</div>
            ) : (
              <div className="space-y-2">
                {inv.entities.filter(e => ['person', 'vehicle', 'car', 'truck', 'object', 'phone'].includes(e.type)).map(ent => (
                  <div
                    key={ent.id}
                    onClick={() => setSelectedEntity(ent.id)}
                    className="p-3 rounded-lg cursor-pointer transition-all"
                    style={{
                      border: `1px solid ${selectedEntity === ent.id ? '#2563eb' : '#e2e8f0'}`,
                      background: selectedEntity === ent.id ? '#eff6ff' : 'white',
                    }}
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <div className="flex items-center gap-2">
                        {ent.type === 'person' ? (
                          <User size={12} style={{ color: '#2563eb' }} />
                        ) : ent.type === 'object' || ent.type === 'phone' ? (
                          <Smartphone size={12} style={{ color: '#0891b2' }} />
                        ) : (
                          <Car size={12} style={{ color: '#7c3aed' }} />
                        )}
                        <span className="font-mono text-[12px] font-bold" style={{ color: '#0f172a' }}>{ent.id}</span>
                      </div>
                      <EntityTypeBadge type={ent.type} />
                    </div>
                    <div className="text-[10px] mb-2" style={{ color: '#94a3b8' }}>
                      Track: {ent.firstSeen} – {ent.lastSeen} ({ent.trackDuration})
                    </div>
                    <ConfidenceMeter value={ent.confidence} size="sm" />
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Entity Detail */}
          {entity && (
            <div className="card p-4 animate-fade-in">
              <div className="section-label mb-3">{entity.id} — Activity Log</div>
              <div className="space-y-1.5">
                {entity.activities.length === 0 ? (
                  <div className="text-[11px] text-slate-500 py-1">No activities logged.</div>
                ) : (
                  entity.activities.map(act => (
                    <div key={act.id} className="flex items-center justify-between py-1.5" style={{ borderBottom: '1px solid #f1f5f9' }}>
                      <div>
                        <div className="text-[11px] font-medium" style={{ color: '#0f172a' }}>{act.label}</div>
                        <div className="font-mono text-[10px]" style={{ color: '#94a3b8' }}>{act.startTime} – {act.endTime}</div>
                      </div>
                      <div className="font-mono text-[11px] font-semibold" style={{ color: '#16a34a' }}>{act.confidence.toFixed(1)}%</div>
                    </div>
                  ))
                )}
              </div>

              {/* Serialized metadata safe from [object Object] */}
              {entity.metadata && (
                <div className="mt-3 pt-3" style={{ borderTop: '1px solid #e2e8f0' }}>
                  <div className="section-label mb-2">Metadata</div>
                  {Object.entries(entity.metadata).map(([k, v]) => (
                    <div key={k} className="flex justify-between text-[10px] py-0.5">
                      <span style={{ color: '#94a3b8' }}>{k.replace(/_/g, ' ')}</span>
                      <span className="font-mono" style={{ color: '#475569' }}>
                        {typeof v === 'object' && v !== null ? JSON.stringify(v) : String(v)}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Camera Info */}
          <div className="card p-4">
            <div className="section-label mb-3 flex items-center gap-2">
              <Camera size={12} />Camera Info
            </div>
            <div className="space-y-1.5">
              {[
                ['Camera ID',    camId],
                ['Location',     normalizeLocationName(inv.location)],
                ['Case',         inv.caseNumber],

                ['Duration',     inv.durationAnalyzed || '00:00:00'],
                ['Investigator', inv.investigator || 'Unassigned'],
                ['Status',       inv.status],
              ].map(([k, v]) => (
                <div key={k} className="flex justify-between text-[11px]">
                  <span style={{ color: '#94a3b8' }}>{k}</span>
                  <span className="font-mono font-medium" style={{ color: '#0f172a' }}>{v}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
