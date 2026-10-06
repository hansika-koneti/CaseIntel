/**
 * CaseIntel — Centralized Investigation State Context
 *
 * Replaces the scattered localStorage + custom DOM events pattern with
 * a single React Context that:
 *  - Holds the active case ID, active video ID, and investigator profile
 *  - Fetches investigation data on demand and caches it in-memory
 *  - Provides typed hooks for all consumers
 *  - Persists user preferences (active case, profile) to localStorage
 *    but treats localStorage as a persistence layer, NOT a communication bus
 */

import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  type ReactNode,
} from 'react';
import { getInvestigation } from '../api/investigations';
import type { Investigation } from '../types';

// ── Investigator Profile ──────────────────────────────────────────────────
export interface InvestigatorProfile {
  name: string;
  role: string;
  badge: string;
  department: string;
  email: string;
}

const DEFAULT_PROFILE: InvestigatorProfile = {
  name: 'Unassigned',
  role: 'Investigator',
  badge: 'Unassigned',
  department: 'CCTV Forensic Division',
  email: '',
};

function loadProfile(): InvestigatorProfile {
  try {
    const raw = localStorage.getItem('investigator-profile');
    if (raw) return JSON.parse(raw) as InvestigatorProfile;
  } catch { /* ignore */ }
  return DEFAULT_PROFILE;
}

// ── Context Shape ─────────────────────────────────────────────────────────
interface CaseIntelContextValue {
  // Active case
  activeCaseId: string | null;
  setActiveCaseId: (id: string | null) => void;

  // Active video
  activeVideoId: string | null;
  setActiveVideoId: (id: string | null) => void;

  // Cached investigation detail for the active case
  investigation: Investigation | null;
  investigationLoading: boolean;
  investigationError: string | null;
  refreshInvestigation: () => Promise<void>;

  // Investigator profile
  profile: InvestigatorProfile;
  updateProfile: (p: InvestigatorProfile) => void;
}

const CaseIntelContext = createContext<CaseIntelContextValue | null>(null);

// ── Provider ──────────────────────────────────────────────────────────────
export function CaseIntelProvider({ children }: { children: ReactNode }) {
  // ── Active Case ID ────────────────────────────────────────────────────
  const [activeCaseId, setActiveCaseIdRaw] = useState<string | null>(() =>
    localStorage.getItem('caseintel-active-case-id'),
  );

  const setActiveCaseId = useCallback((id: string | null) => {
    setActiveCaseIdRaw(id);
    if (id) localStorage.setItem('caseintel-active-case-id', id);
    else localStorage.removeItem('caseintel-active-case-id');
    // Keep legacy event for any remaining consumers during migration
    window.dispatchEvent(new Event('active-case-changed'));
  }, []);

  // ── Active Video ID ───────────────────────────────────────────────────
  const [activeVideoId, setActiveVideoIdRaw] = useState<string | null>(() =>
    localStorage.getItem('caseintel-active-video-id'),
  );

  const setActiveVideoId = useCallback((id: string | null) => {
    setActiveVideoIdRaw(id);
    if (id) localStorage.setItem('caseintel-active-video-id', id);
    else localStorage.removeItem('caseintel-active-video-id');
    window.dispatchEvent(new Event('active-video-changed'));
  }, []);

  // ── Investigation Data ────────────────────────────────────────────────
  const [investigation, setInvestigation] = useState<Investigation | null>(null);
  const [investigationLoading, setInvestigationLoading] = useState(false);
  const [investigationError, setInvestigationError] = useState<string | null>(null);

  const refreshInvestigation = useCallback(async () => {
    if (!activeCaseId) {
      setInvestigation(null);
      setInvestigationError(null);
      return;
    }
    setInvestigationLoading(true);
    setInvestigationError(null);
    try {
      const data = await getInvestigation(activeCaseId);
      setInvestigation(data);
    } catch (e) {
      setInvestigationError(e instanceof Error ? e.message : 'Failed to load investigation');
      setInvestigation(null);
    } finally {
      setInvestigationLoading(false);
    }
  }, [activeCaseId]);

  // Auto-fetch when active case changes
  useEffect(() => {
    refreshInvestigation();
  }, [refreshInvestigation]);

  // ── Investigator Profile ──────────────────────────────────────────────
  const [profile, setProfile] = useState<InvestigatorProfile>(loadProfile);

  const updateProfile = useCallback((p: InvestigatorProfile) => {
    setProfile(p);
    localStorage.setItem('investigator-profile', JSON.stringify(p));
    window.dispatchEvent(new Event('profile-updated'));
  }, []);

  // Listen for profile updates from legacy code (TopBar edit form)
  useEffect(() => {
    const handler = () => setProfile(loadProfile());
    window.addEventListener('profile-updated', handler);
    return () => window.removeEventListener('profile-updated', handler);
  }, []);

  return (
    <CaseIntelContext.Provider
      value={{
        activeCaseId,
        setActiveCaseId,
        activeVideoId,
        setActiveVideoId,
        investigation,
        investigationLoading,
        investigationError,
        refreshInvestigation,
        profile,
        updateProfile,
      }}
    >
      {children}
    </CaseIntelContext.Provider>
  );
}

// ── Hooks ─────────────────────────────────────────────────────────────────

/**
 * Primary hook — returns the full context. Every page that needs case data
 * should call this instead of manually reading localStorage.
 */
export function useCaseIntel(): CaseIntelContextValue {
  const ctx = useContext(CaseIntelContext);
  if (!ctx) throw new Error('useCaseIntel must be used within <CaseIntelProvider>');
  return ctx;
}

/**
 * Convenience hook — returns just the active investigation + loading state.
 */
export function useActiveInvestigation() {
  const { investigation, investigationLoading, investigationError, refreshInvestigation } =
    useCaseIntel();
  return { investigation, loading: investigationLoading, error: investigationError, refresh: refreshInvestigation };
}

/**
 * Convenience hook — returns the investigator profile + updater.
 */
export function useInvestigatorProfile() {
  const { profile, updateProfile } = useCaseIntel();
  return { profile, updateProfile };
}
