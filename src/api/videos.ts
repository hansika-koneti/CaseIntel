/**
 * CaseIntel — Videos API
 *
 * Typed wrappers for multipart video uploads, video analysis execution,
 * pipeline status tracking, and video streaming.
 */

import { apiFetch } from './client';

const BASE_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://127.0.0.1:8000';

export interface VideoUploadMeta {
  cameraId: string;
  location: string;
  investigationId?: string;
  analysisMode?: string;
}

export interface VideoUploadResponse {
  videoId: string;
  filename: string;
  filepath: string;
  sizeBytes: number;
  status: string;
  cameraId: string;
  location: string;
  investigationId?: string;
  metadata?: {
    valid?: boolean;
    fps?: number;
    frameCount?: number;
    width?: number;
    height?: number;
    durationSeconds?: number;
  };
}

export interface VideoStatusResponse {
  videoId: string;
  status: string;
  pipelineStages: Array<{
    id: string;
    label: string;
    status: 'pending' | 'processing' | 'completed' | 'error';
    progress: number;
    processingTimeMs?: number;
    detail?: string;
  }>;
  completedStages: number;
  totalStages: number;
  resultSummary?: string;
}

/**
 * Upload video file via multipart/form-data with real progress tracking.
 */
export function uploadVideo(
  file: File,
  meta: VideoUploadMeta,
  onProgress?: (percent: number) => void,
): Promise<VideoUploadResponse> {
  return new Promise((resolve, reject) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('camera_id', meta.cameraId);
    formData.append('location', meta.location);
    if (meta.investigationId) formData.append('investigation_id', meta.investigationId);
    if (meta.analysisMode) formData.append('analysis_mode', meta.analysisMode);

    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${BASE_URL}/api/videos/upload`);

    if (onProgress && xhr.upload) {
      xhr.upload.onprogress = (evt) => {
        if (evt.lengthComputable) {
          const percent = Math.round((evt.loaded / evt.total) * 100);
          onProgress(percent);
        }
      };
    }

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const json = JSON.parse(xhr.responseText);
          resolve({
            videoId: json.video_id,
            filename: json.filename,
            filepath: json.filepath,
            sizeBytes: json.size_bytes,
            status: json.status,
            cameraId: json.camera_id,
            location: json.location,
            investigationId: json.investigation_id,
            metadata: json.metadata,
          });
        } catch (e) {
          reject(new Error('Invalid JSON response from upload endpoint'));
        }
      } else {
        reject(new Error(`Upload failed with HTTP ${xhr.status}: ${xhr.statusText}`));
      }
    };

    xhr.onerror = () => reject(new Error('Network error during video upload'));
    xhr.send(formData);
  });
}

/**
 * Trigger video analysis pipeline.
 */
export async function analyzeVideo(
  videoId: string,
  config: Record<string, unknown> = {},
): Promise<Record<string, unknown>> {
  return apiFetch<Record<string, unknown>>(`/api/videos/${videoId}/analyze`, {
    method: 'POST',
    body: config,
  });
}

/**
 * Get video pipeline status.
 */
export async function getVideoStatus(videoId: string): Promise<VideoStatusResponse> {
  return apiFetch<VideoStatusResponse>(`/api/videos/${videoId}/status`);
}

export interface VideoInfoResponse {
  id: string;
  investigationId: string | null;
  filename: string;
  cameraId: string;
  location: string;
  status: string;
  uploadedAt: string;
}

/**
 * Get video metadata and associated investigation info.
 */
export async function getVideoInfo(videoId: string): Promise<VideoInfoResponse> {
  return apiFetch<VideoInfoResponse>(`/api/videos/${videoId}`);
}

export interface VideoDetectionResponse {
  videoId: string;
  filename: string;
  valid: boolean;
  fps: number;
  width: number;
  height: number;
  frameCount: number;
  durationSeconds: number;
  analyzedFrames: number;
  detectionsByFrame: Array<{
    frame: number;
    timestampSec: number;
    detections: Array<{
      class: string;
      confidence: number;
      bbox: [number, number, number, number];
      normalizedBbox: [number, number, number, number];
    }>;
  }>;
  summary: {
    totalPersonsDetected: number;
    totalVehiclesDetected: number;
    classesDetected: string[];
  };
}

export interface VideoTrackingResponse {
  videoId: string;
  filename: string;
  valid: boolean;
  fps: number;
  width: number;
  height: number;
  frameCount: number;
  durationSeconds: number;
  analyzedFrames: number;
  tracks: Array<{
    trackId: number;
    entityId: string;
    class: string;
    avgConfidence: number;
    firstSeenSec: number;
    lastSeenSec: number;
    observationsCount: number;
    trajectory: Array<{
      frame: number;
      timestampSec: number;
      x: number;
      y: number;
    }>;
  }>;
  detectionsByFrame: Array<{
    frame: number;
    timestampSec: number;
    detections: Array<{
      trackId?: number;
      entityId: string;
      class: string;
      confidence: number;
      bbox: [number, number, number, number];
      normalizedBbox: [number, number, number, number];
      center: [number, number];
    }>;
  }>;
  summary: {
    totalTrackedEntities: number;
    totalTrackedPersons: number;
    totalTrackedVehicles: number;
    classesDetected: string[];
  };
}

/**
 * Execute real YOLOv11 frame detection.
 */
export async function detectVideo(
  videoId: string,
  options?: { confThresh?: number; sampleFps?: number },
): Promise<VideoDetectionResponse> {
  const qs = new URLSearchParams();
  if (options?.confThresh) qs.set('conf_thresh', String(options.confThresh));
  if (options?.sampleFps) qs.set('sample_fps', String(options.sampleFps));

  return apiFetch<VideoDetectionResponse>(
    `/api/videos/${videoId}/detect${qs.toString() ? `?${qs}` : ''}`,
    { method: 'POST' },
  );
}

/**
 * Execute real YOLOv11 + ByteTrack multi-object tracking.
 */
export async function trackVideo(
  videoId: string,
  options?: { confThresh?: number; sampleFps?: number },
): Promise<VideoTrackingResponse> {
  const qs = new URLSearchParams();
  if (options?.confThresh) qs.set('conf_thresh', String(options.confThresh));
  if (options?.sampleFps) qs.set('sample_fps', String(options.sampleFps));

  return apiFetch<VideoTrackingResponse>(
    `/api/videos/${videoId}/track${qs.toString() ? `?${qs}` : ''}`,
    { method: 'POST' },
  );
}

export interface VideoActionsResponse {
  videoId: string;
  filename: string;
  investigationId?: string;
  tracksAnalyzed: number;
  actions: Array<{
    trackId: number;
    entityId: string;
    class: string;
    durationSec: number;
    actions: Array<{
      action: string;
      confidence: number;
      startTimeSec: number;
      endTimeSec: number;
      severity: string;
      description: string;
    }>;
  }>;
  createdEventsCount: number;
  createdEventIds: string[];
}

/**
 * Execute behavioral action recognition.
 */
export async function classifyVideoActions(
  videoId: string,
  options?: { confThresh?: number; sampleFps?: number },
): Promise<VideoActionsResponse> {
  const qs = new URLSearchParams();
  if (options?.confThresh) qs.set('conf_thresh', String(options.confThresh));
  if (options?.sampleFps) qs.set('sample_fps', String(options.sampleFps));

  return apiFetch<VideoActionsResponse>(
    `/api/videos/${videoId}/actions${qs.toString() ? `?${qs}` : ''}`,
    { method: 'POST' },
  );
}

/**
 * Stream URL for video playback.
 */
export function getVideoStreamUrl(videoId: string): string {
  return `${BASE_URL}/api/videos/${videoId}/stream`;
}
