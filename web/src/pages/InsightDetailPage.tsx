import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import {
  BiasBanner,
  ErrorState,
  LoadingState,
  SectionLabel,
  pretty,
} from '../components/ui'

export function InsightDetailPage() {
  const { insightId = '' } = useParams()
  const { canReview, role } = useAuth()
  const queryClient = useQueryClient()

  const { data, isLoading, error } = useQuery({
    queryKey: ['insight', insightId],
    queryFn: () => api.insight(insightId),
    enabled: Boolean(insightId),
  })

  const mutation = useMutation({
    mutationFn: (status: string) =>
      api.updateInsightStatus(insightId, status, `Updated via dashboard as ${role}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['insight', insightId] })
      queryClient.invalidateQueries({ queryKey: ['insights'] })
      queryClient.invalidateQueries({ queryKey: ['review-stats'] })
    },
  })

  if (isLoading) return <LoadingState label="Loading insight…" />
  if (error || !data) return <ErrorState message={(error as Error)?.message || 'Unknown error'} />

  return (
    <div className="page">
      <p className="crumb">
        <Link to="/insights">Insights</Link> / {data.insight_id}
      </p>
      <div className="page-head">
        <div>
          <h2>{data.statement}</h2>
          <p className="lede">
            {pretty(data.affected_segment)} · confidence {data.confidence} · status {data.status}
          </p>
        </div>
      </div>

      <BiasBanner notes={data.bias_notes || []} sampleSize={data.total_supporting_records} />

      <section className="triptych">
        <article className="panel evidence">
          <SectionLabel>Evidence</SectionLabel>
          <p className="muted small">{data.total_supporting_records} supporting records</p>
          <div className="evidence-list">
            {(data.supporting_evidence || []).map((item) => (
              <blockquote key={item.record_id}>
                <p>“{item.snippet}”</p>
                <footer>
                  {item.source || 'unknown'} · {item.record_id.slice(0, 8)}
                </footer>
              </blockquote>
            ))}
          </div>
        </article>

        <article className="panel interpretation">
          <SectionLabel>Interpretation</SectionLabel>
          <p>{data.business_implication}</p>
          <h4>Open questions</h4>
          <ul>
            {(data.open_questions || []).map((q) => (
              <li key={q}>{q}</li>
            ))}
          </ul>
          <h4>Linked themes</h4>
          <p className="muted">{(data.theme_ids || []).join(', ') || '—'}</p>
        </article>

        <article className="panel recommendation">
          <SectionLabel>Recommendation</SectionLabel>
          <p>
            Treat this as a directional finding for experiment design, not proof of causality.
          </p>
          <p>
            Primary barriers: {(data.primary_barriers || []).map(pretty).join(', ') || '—'}
          </p>
          {canReview ? (
            <div className="button-row">
              <button onClick={() => mutation.mutate('approved')} disabled={mutation.isPending}>
                Approve
              </button>
              <button
                className="secondary"
                onClick={() => mutation.mutate('hypothesis')}
                disabled={mutation.isPending}
              >
                Mark hypothesis
              </button>
              <button
                className="danger"
                onClick={() => mutation.mutate('rejected')}
                disabled={mutation.isPending}
              >
                Reject
              </button>
            </div>
          ) : (
            <p className="muted small">Switch to reviewer/admin to change status.</p>
          )}
          {mutation.isError && (
            <p className="error-text">{(mutation.error as Error).message}</p>
          )}
        </article>
      </section>
    </div>
  )
}
