import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider } from './auth/AuthContext'
import { ThemeProvider } from './theme/ThemeContext'
import { AppShell } from './components/AppShell'
import { OverviewPage } from './pages/OverviewPage'
import { InsightsPage } from './pages/InsightsPage'
import { InsightDetailPage } from './pages/InsightDetailPage'
import { OpportunitiesPage } from './pages/OpportunitiesPage'
import { ExperimentsPage } from './pages/ExperimentsPage'
import { ReviewQueuePage } from './pages/ReviewQueuePage'
import { PipelineJobsPage } from './pages/PipelineJobsPage'
import { SourceAnalysisPage } from './pages/SourceAnalysisPage'
import { ReviewDiscoveryPage } from './pages/ReviewDiscoveryPage'
import { DiscoveryChallengesPage } from './pages/DiscoveryChallengesPage'
import { ThemeExplorerPage } from './pages/ThemeExplorerPage'
import { SegmentExplorerPage } from './pages/SegmentExplorerPage'
import { RootCauseAnalysisPage } from './pages/RootCauseAnalysisPage'
import { UnmetNeedsPage } from './pages/UnmetNeedsPage'
import { DiscoveryJourneyPage } from './pages/DiscoveryJourneyPage'
import { ValidationPage } from './pages/ValidationPage'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 15_000,
    },
  },
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <AuthProvider>
          <BrowserRouter>
            <Routes>
              <Route element={<AppShell />}>
                <Route index element={<OverviewPage />} />
                <Route path="sources" element={<SourceAnalysisPage />} />
                <Route path="reviews" element={<ReviewDiscoveryPage />} />
                <Route path="challenges" element={<DiscoveryChallengesPage />} />
                <Route path="themes" element={<ThemeExplorerPage />} />
                <Route path="segments" element={<SegmentExplorerPage />} />
                <Route path="root-causes" element={<RootCauseAnalysisPage />} />
                <Route path="unmet-needs" element={<UnmetNeedsPage />} />
                <Route path="journey" element={<DiscoveryJourneyPage />} />
                <Route path="validation" element={<ValidationPage />} />
                <Route path="insights" element={<InsightsPage />} />
                <Route path="insights/:insightId" element={<InsightDetailPage />} />
                <Route path="opportunities" element={<OpportunitiesPage />} />
                <Route path="experiments" element={<ExperimentsPage />} />
                <Route path="review" element={<ReviewQueuePage />} />
                <Route path="jobs" element={<PipelineJobsPage />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Route>
            </Routes>
          </BrowserRouter>
        </AuthProvider>
      </ThemeProvider>
    </QueryClientProvider>
  )
}
