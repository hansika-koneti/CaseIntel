import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import MainLayout from './components/layout/MainLayout';
import OverviewPage from './pages/OverviewPage';
import InvestigationsPage from './pages/InvestigationsPage';
import CCTVAnalysisPage from './pages/CCTVAnalysisPage';
import VideoAnalysisPage from './pages/VideoAnalysisPage';
import EventTimelinePage from './pages/EventTimelinePage';
import KnowledgeGraphPage from './pages/KnowledgeGraphPage';
import IncidentAnalysisPage from './pages/IncidentAnalysisPage';
import EvidencePage from './pages/EvidencePage';
import InvestigationReportPage from './pages/InvestigationReportPage';
import NotFoundPage from './pages/NotFoundPage';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<OverviewPage />} />
          <Route path="investigations" element={<InvestigationsPage />} />
          <Route path="cctv-analysis" element={<CCTVAnalysisPage />} />
          <Route path="cctv-analysis/video" element={<VideoAnalysisPage />} />
          <Route path="timeline" element={<EventTimelinePage />} />
          <Route path="graph" element={<KnowledgeGraphPage />} />
          <Route path="incident" element={<IncidentAnalysisPage />} />
          <Route path="evidence" element={<EvidencePage />} />
          <Route path="report" element={<InvestigationReportPage />} />
          {/* Fallback */}
          <Route path="404" element={<NotFoundPage />} />
          <Route path="*" element={<Navigate to="/404" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
