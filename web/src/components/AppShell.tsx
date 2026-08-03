import { Link, NavLink, Outlet } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { useTheme } from '../theme/ThemeContext'
import type { JobKind, RoleName } from '../types/api'

const NAV = [
  { to: '/', label: 'Executive Summary', icon: '📊' },
  { to: '/sources', label: 'Source Analysis', icon: '📁' },
  { to: '/reviews', label: 'Review Discovery', icon: '🔎' },
  { to: '/challenges', label: 'Discovery Challenges', icon: '🚧' },
  { to: '/themes', label: 'Theme Explorer', icon: '🏷️' },
  { to: '/segments', label: 'Segment Explorer', icon: '👥' },
  { to: '/root-causes', label: 'Root Cause Analysis', icon: '🎯' },
  { to: '/unmet-needs', label: 'Unmet Needs', icon: '💡' },
  { to: '/journey', label: 'Discovery Journey', icon: '🗺️' },
  { to: '/validation', label: 'Validation', icon: '✅' },
  { to: '/insights', label: 'Insights', icon: '🧠' },
  { to: '/opportunities', label: 'Opportunities', icon: '🚀' },
  { to: '/experiments', label: 'Experiments', icon: '🧪' },
  { to: '/review', label: 'Review Queue', icon: '📝' },
  { to: '/jobs', label: 'Pipeline Jobs', icon: '⚙️' },
]

const PIPELINE_ACTIONS: Array<{ kind: JobKind; label: string; primary?: boolean }> = [
  { kind: 'analysis_cascade', label: 'Run Full Analysis', primary: true },
  { kind: 'ingest_play', label: 'Fetch Play Store Reviews' },
  { kind: 'ingest_appstore', label: 'Fetch App Store Reviews' },
  { kind: 'ingest_all', label: 'Fetch All Store Reviews' },
  { kind: 'ingest_reddit_selenium', label: 'Fetch Reddit Discussions' },
  { kind: 'enrich', label: 'Resume Enrichment' },
]

export function AppShell() {
  const { role, canReview, canRunJobs, setRole } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const queryClient = useQueryClient()

  const jobsQuery = useQuery({
    queryKey: ['jobs'],
    queryFn: api.jobs,
    refetchInterval: 5000,
  })
  const researchQuery = useQuery({
    queryKey: ['research-summary'],
    queryFn: api.researchSummary,
    refetchInterval: 15000,
  })

  const startMutation = useMutation({
    mutationFn: (kind: JobKind) => api.startJob(kind),
    onSuccess: () => {
      queryClient.invalidateQueries()
    },
  })

  const activeJob = jobsQuery.data?.active_job
  const research = researchQuery.data
  const busy = startMutation.isPending || Boolean(activeJob)

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <p className="brand-kicker">Swiggy Instamart</p>
          <h1>Research Intelligence</h1>
          <p className="brand-sub">Product Research Intelligence Platform</p>
        </div>

        <nav className="nav">
          {NAV.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.to === '/'}>
              <span className="nav-icon">{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-section">
          <h3>Pipeline Actions</h3>
          {canRunJobs ? (
            <div className="sidebar-actions">
              {PIPELINE_ACTIONS.map((action) => (
                <button
                  key={action.kind}
                  className={action.primary ? 'sidebar-btn primary' : 'sidebar-btn'}
                  onClick={() => startMutation.mutate(action.kind)}
                  disabled={busy}
                  title={activeJob ? 'Wait for the active job to finish' : undefined}
                >
                  {action.label}
                </button>
              ))}
            </div>
          ) : (
            <p className="muted small">Switch to Admin to run pipeline actions.</p>
          )}
          {startMutation.isError && (
            <p className="error-text small">{(startMutation.error as Error).message}</p>
          )}
          {startMutation.isSuccess && (
            <p className="muted small">Started {startMutation.data.job_type}</p>
          )}
        </div>

        <div className="sidebar-section">
          <h3>Pipeline Status</h3>
          <p className="muted small">
            Last pipeline: <code>{research?.pipeline_status.last_job?.status || 'idle'}</code>
          </p>
          {activeJob && (
            <p className="muted small">
              Active: {activeJob.job_type} · {activeJob.status}
            </p>
          )}
          <p className="muted small">
            Themes: {research?.portfolio.themes_discovered ?? 0} | Insights:{' '}
            {research?.portfolio.insights_count ?? 0} | Opportunities:{' '}
            {research?.portfolio.opportunities_count ?? 0}
          </p>
          <p className="muted small">
            Total in DB: {research?.portfolio.reviews_ingested?.toLocaleString() ?? 0}
          </p>
          <p className="muted small">
            Play: {research?.portfolio.play_store ?? 0} | App: {research?.portfolio.app_store ?? 0} |
            Reddit: {research?.portfolio.reddit ?? 0}
          </p>
        </div>

        <div className="role-box">
          <label htmlFor="role">Signed in as</label>
          <select id="role" value={role} onChange={(e) => setRole(e.target.value as RoleName)}>
            <option value="viewer">Viewer</option>
            <option value="reviewer">Reviewer</option>
            <option value="admin">Admin</option>
          </select>
          <p className="muted small">
            {canRunJobs
              ? 'Admin can run jobs.'
              : canReview
                ? 'Reviewer can approve insights.'
                : 'Viewer is read-only.'}
          </p>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div>
            <p className="eyebrow">Product Research Intelligence</p>
            <p className="muted">Evidence-backed insights for growth, product, and research</p>
          </div>
          <div className="topbar-actions">
            <button
              type="button"
              className="theme-toggle"
              onClick={toggleTheme}
              aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}
              title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}
            >
              <span aria-hidden="true">{theme === 'dark' ? '☀️' : '🌙'}</span>
              {theme === 'dark' ? 'Light' : 'Dark'}
            </button>
            <Link className="ghost-link" to="/jobs">
              Pipeline status
            </Link>
          </div>
        </header>
        <Outlet />
      </main>
    </div>
  )
}
