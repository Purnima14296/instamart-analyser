import { useState } from 'react'
import type { FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { EmptyState, ErrorState, LoadingState, pretty } from '../components/ui'

export function ReviewQueuePage() {
  const { canReview, role } = useAuth()
  const queryClient = useQueryClient()
  const draftsQuery = useQuery({
    queryKey: ['insights', 'draft'],
    queryFn: () => api.insights({ status: 'draft' }),
  })
  const approvedQuery = useQuery({
    queryKey: ['insights', 'approved'],
    queryFn: () => api.insights({ status: 'approved' }),
  })
  const statsQuery = useQuery({
    queryKey: ['review-stats'],
    queryFn: api.reviewStats,
  })

  const [reviewer, setReviewer] = useState('dashboard_reviewer')
  const [feedbackRole, setFeedbackRole] = useState<'product' | 'research' | 'growth' | 'other'>(
    'growth',
  )
  const [comment, setComment] = useState('')
  const [defect, setDefect] = useState('')
  const [feedbackMsg, setFeedbackMsg] = useState('')

  const statusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      api.updateInsightStatus(id, status, `Review queue action as ${role}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['insights'] })
      queryClient.invalidateQueries({ queryKey: ['review-stats'] })
      queryClient.invalidateQueries({ queryKey: ['overview'] })
    },
  })

  const feedbackMutation = useMutation({
    mutationFn: api.submitFeedback,
    onSuccess: (result) => {
      const refresh = result.phase5_feedback_refresh
      setFeedbackMsg(
        refresh
          ? `Feedback submitted. Phase 5 summary now has ${refresh.response_count} responses.`
          : 'Feedback submitted.',
      )
      setComment('')
      setDefect('')
      queryClient.invalidateQueries({ queryKey: ['feedback'] })
    },
    onError: (err) => setFeedbackMsg((err as Error).message),
  })

  function onSubmitFeedback(event: FormEvent) {
    event.preventDefault()
    if (!canReview) return
    feedbackMutation.mutate({
      reviewer,
      role: feedbackRole,
      overall_usefulness: 'high',
      trust_in_outputs: 'medium',
      would_use_for_experiment_planning: true,
      comments: comment ? [comment] : ['Reviewed draft insights in dashboard'],
      defects: defect
        ? [{ issue: defect, severity: 'medium', status: 'open' }]
        : [],
    })
  }

  if (draftsQuery.isLoading) return <LoadingState label="Loading review queue…" />
  if (draftsQuery.error || !draftsQuery.data) {
    return <ErrorState message={(draftsQuery.error as Error)?.message || 'Unknown error'} />
  }

  const drafts = draftsQuery.data.insights
  const approved = approvedQuery.data?.insights || []
  const stats = statsQuery.data

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h2>Review queue</h2>
          <p className="lede">Draft insights waiting for human validation.</p>
        </div>
      </div>

      <section className="metric-row">
        <article className="metric">
          <span>Drafts</span>
          <strong>{drafts.length}</strong>
          <em>awaiting decision</em>
        </article>
        <article className="metric">
          <span>Approved</span>
          <strong>{approved.length}</strong>
          <em>ready for growth</em>
        </article>
        <article className="metric">
          <span>Reviewed total</span>
          <strong>{stats?.reviewed_count ?? 0}</strong>
          <em>status overrides saved</em>
        </article>
        <article className="metric">
          <span>Your role</span>
          <strong>{role}</strong>
          <em>{canReview ? 'can decide' : 'read-only'}</em>
        </article>
      </section>

      {!drafts.length ? (
        <EmptyState message="No draft insights in the queue." />
      ) : (
        <div className="stack">
          {drafts.map((insight) => (
            <article key={insight.insight_id} className="panel">
              <div className="card-meta">
                <span className={`chip ${insight.confidence}`}>{insight.confidence}</span>
                <span className="chip soft">{pretty(insight.affected_segment)}</span>
              </div>
              <h3>
                <Link to={`/insights/${insight.insight_id}`}>{insight.statement}</Link>
              </h3>
              <p className="muted">{insight.total_supporting_records} supporting reviews</p>
              {insight.supporting_evidence?.[0] && (
                <blockquote>“{insight.supporting_evidence[0].snippet}”</blockquote>
              )}
              {canReview ? (
                <div className="button-row">
                  <button
                    onClick={() =>
                      statusMutation.mutate({ id: insight.insight_id, status: 'approved' })
                    }
                    disabled={statusMutation.isPending}
                  >
                    Approve
                  </button>
                  <button
                    className="secondary"
                    onClick={() =>
                      statusMutation.mutate({ id: insight.insight_id, status: 'hypothesis' })
                    }
                    disabled={statusMutation.isPending}
                  >
                    Hypothesis
                  </button>
                  <button
                    className="danger"
                    onClick={() =>
                      statusMutation.mutate({ id: insight.insight_id, status: 'rejected' })
                    }
                    disabled={statusMutation.isPending}
                  >
                    Reject
                  </button>
                </div>
              ) : (
                <p className="muted small">Switch to reviewer/admin to act on drafts.</p>
              )}
              {statusMutation.isError && (
                <p className="error-text">{(statusMutation.error as Error).message}</p>
              )}
            </article>
          ))}
        </div>
      )}

      <section className="panel">
        <h3>Stakeholder feedback</h3>
        <p className="muted small">
          Submissions sync into the Phase 5 stakeholder feedback summary.
        </p>
        <form className="feedback-form" onSubmit={onSubmitFeedback}>
          <label>
            Reviewer name
            <input value={reviewer} onChange={(e) => setReviewer(e.target.value)} required />
          </label>
          <label>
            Role
            <select
              value={feedbackRole}
              onChange={(e) =>
                setFeedbackRole(e.target.value as 'product' | 'research' | 'growth' | 'other')
              }
            >
              <option value="product">Product</option>
              <option value="research">Research</option>
              <option value="growth">Growth</option>
              <option value="other">Other</option>
            </select>
          </label>
          <label>
            Comment
            <textarea
              rows={4}
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="What should product/growth know?"
            />
          </label>
          <label>
            Open defect (optional)
            <input
              value={defect}
              onChange={(e) => setDefect(e.target.value)}
              placeholder="e.g. Need clearer segment eligibility rules"
            />
          </label>
          <button type="submit" disabled={!canReview || feedbackMutation.isPending}>
            Submit feedback
          </button>
          {!canReview && (
            <p className="muted small">Reviewer or admin role required to submit feedback.</p>
          )}
          {feedbackMsg && <p className="muted small">{feedbackMsg}</p>}
        </form>
      </section>
    </div>
  )
}
