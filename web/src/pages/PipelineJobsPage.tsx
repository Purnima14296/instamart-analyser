import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import type { JobKind } from '../types/api'
import { ErrorState, LoadingState } from '../components/ui'

const INGEST_JOBS: Array<{ kind: JobKind; label: string }> = [
  { kind: 'ingest_play', label: 'Fetch Play Store reviews' },
  { kind: 'ingest_appstore', label: 'Fetch App Store reviews' },
  { kind: 'ingest_reddit_selenium', label: 'Fetch Reddit discussions' },
  { kind: 'ingest_all', label: 'Fetch all store + Reddit' },
]

const ANALYSIS_JOBS: Array<{ kind: JobKind; label: string; primary?: boolean }> = [
  { kind: 'analysis_cascade', label: 'Run analysis cascade', primary: true },
  { kind: 'enrich', label: 'Resume enrichment' },
  { kind: 'phase3', label: 'Refresh Phase 3' },
  { kind: 'phase4', label: 'Refresh Phase 4' },
  { kind: 'phase5', label: 'Refresh Phase 5' },
]

export function PipelineJobsPage() {
  const { canRunJobs } = useAuth()
  const queryClient = useQueryClient()

  const enrichmentQuery = useQuery({
    queryKey: ['enrichment-status'],
    queryFn: api.enrichmentStatus,
    refetchInterval: 5000,
  })
  const jobsQuery = useQuery({
    queryKey: ['jobs'],
    queryFn: api.jobs,
    refetchInterval: 3000,
  })
  const researchQuery = useQuery({
    queryKey: ['research-summary'],
    queryFn: api.researchSummary,
    refetchInterval: 8000,
  })
  const limitationsQuery = useQuery({
    queryKey: ['limitations'],
    queryFn: api.limitations,
  })

  const startMutation = useMutation({
    mutationFn: (kind: JobKind) => api.startJob(kind),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      queryClient.invalidateQueries({ queryKey: ['enrichment-status'] })
      queryClient.invalidateQueries({ queryKey: ['overview'] })
      queryClient.invalidateQueries({ queryKey: ['research-summary'] })
    },
  })

  const recoverMutation = useMutation({
    mutationFn: api.recoverStaleJobs,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['jobs'] }),
  })

  if (enrichmentQuery.isLoading || jobsQuery.isLoading) {
    return <LoadingState label="Loading pipeline jobs…" />
  }
  if (enrichmentQuery.error || jobsQuery.error) {
    return (
      <ErrorState
        message={
          (enrichmentQuery.error as Error)?.message ||
          (jobsQuery.error as Error)?.message ||
          'Unknown error'
        }
      />
    )
  }

  const enrichment = enrichmentQuery.data!
  const jobs = jobsQuery.data?.jobs || []
  const activeJob = jobsQuery.data?.active_job
  const research = researchQuery.data
  const busy = startMutation.isPending || Boolean(activeJob)
  const enrichDisabled =
    !canRunJobs ||
    busy ||
    Boolean(enrichment.quota_blocked) ||
    !enrichment.can_start_enrichment

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h2>Pipeline jobs</h2>
          <p className="lede">
            Ingest feedback, resume enrichment, and refresh Phase 3–5 research outputs.
          </p>
        </div>
      </div>

      {research && (
        <section className="status-strip">
          <div>
            <span>Source mix</span>
            <strong>{research.portfolio.reviews_ingested.toLocaleString()}</strong>
            <em>
              Play {research.portfolio.play_store} · App {research.portfolio.app_store} · Reddit{' '}
              {research.portfolio.reddit}
            </em>
          </div>
          <div>
            <span>Themes / insights</span>
            <strong>
              {research.portfolio.themes_discovered} / {research.portfolio.insights_count}
            </strong>
            <em>{research.portfolio.opportunities_count} opportunities</em>
          </div>
          <div>
            <span>Pending enrichment</span>
            <strong>{research.portfolio.analysis_pending}</strong>
            <em>{research.portfolio.coverage_pct}% coverage</em>
          </div>
          <div>
            <span>Last job</span>
            <strong>{research.pipeline_status.last_job?.job_type || '—'}</strong>
            <em>{research.pipeline_status.last_job?.status || 'idle'}</em>
          </div>
        </section>
      )}

      {enrichment.quota_blocked && (
        <aside className="bias-banner">
          <strong>Daily quota / rate-limit state</strong>
          <p>{enrichment.quota_message}</p>
          <p className="muted small">
            Remaining tokens estimate:{' '}
            {enrichment.usage_today.remaining_token_estimate ?? 'n/a'}
          </p>
        </aside>
      )}

      {activeJob && (
        <aside className="bias-banner">
          <strong>Active job</strong>
          <p>
            {activeJob.job_type} · {activeJob.status} · {activeJob.job_id}
          </p>
          <p className="muted small">{activeJob.message}</p>
        </aside>
      )}

      <section className="metric-row">
        <article className="metric">
          <span>Coverage</span>
          <strong>
            {enrichment.enriched_count}/{enrichment.cohort_size}
          </strong>
          <em>{enrichment.coverage_pct}%</em>
        </article>
        <article className="metric">
          <span>Used today</span>
          <strong>{enrichment.usage_today.enrichment_calls}</strong>
          <em>of {enrichment.usage_today.limits.enrichment_daily_cap}</em>
        </article>
        <article className="metric">
          <span>Remaining today</span>
          <strong>{enrichment.usage_today.remaining_enrichment_estimate}</strong>
          <em>enrichment slots</em>
        </article>
        <article className="metric">
          <span>Still to enrich</span>
          <strong>{enrichment.remaining_to_enrich ?? '—'}</strong>
          <em>{enrichment.groq_key_configured ? 'key configured' : 'key missing'}</em>
        </article>
      </section>

      <section className="panel">
        <h3>Pipeline actions · ingest</h3>
        {canRunJobs ? (
          <div className="button-row">
            {INGEST_JOBS.map((job) => (
              <button
                key={job.kind}
                className="secondary"
                onClick={() => startMutation.mutate(job.kind)}
                disabled={busy}
              >
                {job.label}
              </button>
            ))}
          </div>
        ) : (
          <p className="muted">Admin role required to trigger ingest jobs.</p>
        )}
      </section>

      <section className="panel">
        <h3>Pipeline actions · analysis</h3>
        {canRunJobs ? (
          <div className="button-row">
            {ANALYSIS_JOBS.map((job) => (
              <button
                key={job.kind}
                className={job.primary ? undefined : 'secondary'}
                onClick={() => startMutation.mutate(job.kind)}
                disabled={job.kind === 'enrich' ? enrichDisabled : busy}
                title={
                  job.kind === 'enrich' && enrichment.quota_blocked
                    ? enrichment.quota_message
                    : activeJob
                      ? 'Wait for the active job to finish'
                      : undefined
                }
              >
                {job.label}
              </button>
            ))}
            <button
              className="secondary"
              onClick={() => recoverMutation.mutate()}
              disabled={recoverMutation.isPending}
            >
              Recover stale jobs
            </button>
          </div>
        ) : (
          <p className="muted">Admin role required to trigger jobs.</p>
        )}
        {enrichDisabled && canRunJobs && (
          <p className="muted small">
            Enrichment is disabled while quota is exhausted, another job is active, or the cohort is
            complete. Cascade can still refresh Phase 3–5 if enrich is skipped.
          </p>
        )}
        {startMutation.isError && (
          <p className="error-text">{(startMutation.error as Error).message}</p>
        )}
        {startMutation.isSuccess && (
          <p className="muted small">
            Started {startMutation.data.job_type}: {startMutation.data.job_id}
          </p>
        )}
        {recoverMutation.isSuccess && (
          <p className="muted small">Recovered {recoverMutation.data.recovered} stale job(s).</p>
        )}
      </section>

      <section className="stack">
        <h3>Recent jobs</h3>
        {jobs.map((job) => (
          <article key={job.job_id} className="panel">
            <div className="card-meta">
              <span className="chip soft">{job.job_type}</span>
              <span className={`chip ${job.status}`}>{job.status}</span>
              {job.failure_class && <span className="chip low">{job.failure_class}</span>}
            </div>
            <p>
              <strong>{job.job_id}</strong>
            </p>
            <p className="muted small">{job.message}</p>
            {job.error && <p className="error-text">{job.error}</p>}
            {job.recovery_hint && <p className="muted small">Recovery: {job.recovery_hint}</p>}
            <p className="muted small">Created {job.created_at}</p>
          </article>
        ))}
        {!jobs.length && <p className="muted">No jobs yet.</p>}
      </section>

      <section className="panel">
        <h3>Known limitations</h3>
        <ul>
          {(limitationsQuery.data?.limitations || []).map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </section>
    </div>
  )
}
