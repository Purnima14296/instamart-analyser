import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { BiasBanner, EmptyState, ErrorState, LoadingState, pretty } from '../components/ui'

export function InsightsPage() {
  const [confidence, setConfidence] = useState('')
  const [status, setStatus] = useState('')
  const { data, isLoading, error } = useQuery({
    queryKey: ['insights', confidence, status],
    queryFn: () =>
      api.insights({
        confidence: confidence || undefined,
        status: status || undefined,
      }),
  })

  const segments = useMemo(() => {
    const set = new Set((data?.insights || []).map((i) => i.affected_segment))
    return Array.from(set)
  }, [data])

  if (isLoading) return <LoadingState label="Loading insights…" />
  if (error || !data) return <ErrorState message={(error as Error)?.message || 'Unknown error'} />

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h2>Insights</h2>
          <p className="lede">Each insight is linked to supporting review evidence.</p>
        </div>
      </div>

      <BiasBanner notes={data.bias_notes || []} />

      <div className="filters">
        <label>
          Confidence
          <select value={confidence} onChange={(e) => setConfidence(e.target.value)}>
            <option value="">All</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </label>
        <label>
          Status
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">All</option>
            <option value="draft">Draft</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
            <option value="hypothesis">Hypothesis</option>
          </select>
        </label>
        <p className="muted small">{data.count} insights · segments seen: {segments.length}</p>
      </div>

      {!data.insights.length ? (
        <EmptyState message="No insights match these filters." />
      ) : (
        <div className="card-grid">
          {data.insights.map((insight) => (
            <Link key={insight.insight_id} to={`/insights/${insight.insight_id}`} className="insight-card">
              <div className="card-meta">
                <span className={`chip ${insight.confidence}`}>{insight.confidence}</span>
                <span className="chip soft">{insight.status}</span>
              </div>
              <h3>{insight.statement}</h3>
              <p className="muted">
                {pretty(insight.affected_segment)} · {insight.total_supporting_records} supporting
                reviews
              </p>
              {insight.supporting_evidence?.[0] && (
                <blockquote>
                  “{insight.supporting_evidence[0].snippet}”
                </blockquote>
              )}
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
