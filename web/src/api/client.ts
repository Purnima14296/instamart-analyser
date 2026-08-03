import type {
  FeedbackPayload,
  InsightsResponse,
  MeasurementFramework,
  Opportunity,
  OverviewResponse,
  Hypothesis,
  Insight,
  Job,
  JobKind,
  ResearchSummary,
  RoleName,
  SourceAnalysis,
  ReviewSearchResponse,
  DiscoveryChallenges,
  SegmentExplorer,
  RootCauseAnalysis,
  UnmetNeeds,
  DiscoveryJourney,
  ValidationReport,
  ThemesResponse,
} from '../types/api'

const API_BASE = (import.meta.env.VITE_API_BASE ?? '').replace(/\/$/, '')

const TOKEN_STORAGE_KEY = 'instamart_api_token'
const ROLE_STORAGE_KEY = 'instamart_api_role'

export const DEMO_TOKENS: Record<RoleName, string> = {
  viewer: import.meta.env.VITE_API_VIEWER_TOKEN || 'viewer-demo-token',
  reviewer: import.meta.env.VITE_API_REVIEWER_TOKEN || 'reviewer-demo-token',
  admin: import.meta.env.VITE_API_ADMIN_TOKEN || 'admin-demo-token',
}

export function getStoredToken(): string {
  return localStorage.getItem(TOKEN_STORAGE_KEY) || DEMO_TOKENS.viewer
}

export function getStoredRole(): RoleName {
  return (localStorage.getItem(ROLE_STORAGE_KEY) as RoleName) || 'viewer'
}

export function setAuth(role: RoleName, token?: string) {
  localStorage.setItem(ROLE_STORAGE_KEY, role)
  localStorage.setItem(TOKEN_STORAGE_KEY, token || DEMO_TOKENS[role])
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  headers.set('Authorization', `Bearer ${getStoredToken()}`)
  if (init.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
  })

  if (!response.ok) {
    let detail = response.statusText
    try {
      const payload = await response.json()
      detail = payload.detail || JSON.stringify(payload)
    } catch {
      // ignore parse errors
    }
    throw new Error(`${response.status}: ${detail}`)
  }

  return response.json() as Promise<T>
}

export const api = {
  health: () => request<{ status: string; role: string }>('/api/health'),
  overview: () => request<OverviewResponse>('/api/overview'),
  researchSummary: () => request<ResearchSummary>('/api/research/summary'),
  exploreSources: () => request<SourceAnalysis>('/api/explore/sources'),
  exploreReviews: (params?: {
    q?: string
    source?: string
    sentiment?: string
    segment?: string
    mission?: string
    barrier?: string
    enriched_only?: boolean
    limit?: number
    offset?: number
  }) => {
    const query = new URLSearchParams()
    Object.entries(params || {}).forEach(([key, value]) => {
      if (value !== undefined && value !== '' && value !== false) {
        query.set(key, String(value))
      }
    })
    const suffix = query.toString() ? `?${query}` : ''
    return request<ReviewSearchResponse>(`/api/explore/reviews${suffix}`)
  },
  exploreChallenges: () => request<DiscoveryChallenges>('/api/explore/discovery-challenges'),
  exploreSegments: () => request<SegmentExplorer>('/api/explore/segments'),
  exploreRootCauses: () => request<RootCauseAnalysis>('/api/explore/root-causes'),
  exploreUnmetNeeds: () => request<UnmetNeeds>('/api/explore/unmet-needs'),
  exploreJourney: () => request<DiscoveryJourney>('/api/explore/journey'),
  exploreValidation: () => request<ValidationReport>('/api/explore/validation'),
  enrichmentStatus: () => request<OverviewResponse['enrichment']>('/api/enrichment/status'),
  insights: (params?: { confidence?: string; status?: string; segment?: string }) => {
    const query = new URLSearchParams()
    if (params?.confidence) query.set('confidence', params.confidence)
    if (params?.status) query.set('status', params.status)
    if (params?.segment) query.set('segment', params.segment)
    const suffix = query.toString() ? `?${query}` : ''
    return request<InsightsResponse>(`/api/insights${suffix}`)
  },
  insight: (id: string) => request<Insight>(`/api/insights/${id}`),
  updateInsightStatus: (id: string, status: string, notes?: string) =>
    request<Insight>(`/api/insights/${id}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status, notes }),
    }),
  themes: () => request<ThemesResponse>('/api/themes'),
  opportunities: () =>
    request<{ opportunities: Opportunity[]; input_summary?: Record<string, unknown> }>(
      '/api/opportunities',
    ),
  hypotheses: () =>
    request<{ hypotheses: Hypothesis[]; input_summary?: Record<string, unknown> }>(
      '/api/hypotheses',
    ),
  measurement: () => request<MeasurementFramework>('/api/measurement'),
  report: (name: string) =>
    request<{ name: string; format: string; content: string | Record<string, unknown> }>(
      `/api/reports/${name}`,
    ),
  jobs: () =>
    request<{ count: number; active_count: number; active_job: Job | null; jobs: Job[] }>(
      '/api/jobs',
    ),
  job: (id: string) => request<Job>(`/api/jobs/${id}`),
  startJob: (kind: JobKind) =>
    request<{ job_id: string; job_type: string; status: string; message: string }>(
      `/api/jobs/${kind}`,
      { method: 'POST' },
    ),
  recoverStaleJobs: () =>
    request<{ recovered: number }>('/api/jobs/recover-stale', { method: 'POST' }),
  feedback: () => request<{ count: number; responses: unknown[] }>('/api/feedback'),
  reviewStats: () =>
    request<{ reviewed_count: number; status_breakdown: Record<string, number> }>(
      '/api/feedback/review-stats',
    ),
  submitFeedback: (payload: FeedbackPayload) =>
    request<{
      status: string
      feedback_id: string
      phase5_feedback_refresh?: {
        added_from_api: number
        response_count: number
        open_defects: number
      }
    }>('/api/feedback', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  limitations: () =>
    request<{
      limitations: string[]
      operational_notes: string[]
      enrichment: OverviewResponse['enrichment']
    }>('/api/system/limitations'),
  me: () =>
    request<{
      role: string
      permissions: { can_view: boolean; can_review: boolean; can_run_jobs: boolean }
    }>('/api/me'),
}
