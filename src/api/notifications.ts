/**
 * CaseIntel — Live Notifications API
 * Typed wrapper for /api/notifications.
 */

import { apiFetch } from './client';

export interface NotificationItem {
  id: string;
  type: 'suspicious_event' | 'evidence' | 'incident' | 'video_analysis' | 'report';
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO';
  title: string;
  message: string;
  timestamp: string;
  createdAt: string;
  investigationId: string;
  caseNumber: string;
  link: string;
  actionLabel?: string;
  isRead?: boolean;
}

export interface NotificationsResponse {
  notifications: NotificationItem[];
  total: number;
  investigationId?: string;
}

export async function getNotifications(investigationId?: string): Promise<NotificationsResponse> {
  const query = investigationId ? `?investigation_id=${encodeURIComponent(investigationId)}` : '';
  return apiFetch<NotificationsResponse>(`/api/notifications${query}`);
}
