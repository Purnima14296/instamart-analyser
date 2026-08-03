import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { ErrorState, LoadingState, SectionLabel } from '../components/ui'

export function ExperimentsPage() {
  const hypothesesQuery = useQuery({ queryKey: ['hypotheses'], queryFn: api.hypotheses })
  const measurementQuery = useQuery({ queryKey: ['measurement'], queryFn: api.measurement })
  const handoffQuery = useQuery({
    queryKey: ['report', 'growth-handoff-package'],
    queryFn: () => api.report('growth-handoff-package'),
  })

  if (hypothesesQuery.isLoading || measurementQuery.isLoading) {
    return <LoadingState label="Loading experiment backlog…" />
  }
  if (hypothesesQuery.error || measurementQuery.error) {
    return (
      <ErrorState
        message={
          (hypothesesQuery.error as Error)?.message ||
          (measurementQuery.error as Error)?.message ||
          'Unknown error'
        }
      />
    )
  }

  const hypotheses = hypothesesQuery.data?.hypotheses || []
  const measurement = measurementQuery.data!

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h2>Experiments</h2>
          <p className="lede">Hypothesis backlog and measurement readiness for growth testing.</p>
        </div>
      </div>

      <section className="panel">
        <SectionLabel>North star</SectionLabel>
        <p>{measurement.north_star}</p>
      </section>

      <section className="split-grid">
        <article className="panel">
          <h3>Core metrics</h3>
          <ul className="metric-defs">
            {measurement.core_metrics.map((metric) => (
              <li key={metric.metric_id}>
                <strong>{metric.name}</strong>
                <p>{metric.definition}</p>
              </li>
            ))}
          </ul>
        </article>
        <article className="panel">
          <h3>Guardrails</h3>
          <ul className="metric-defs">
            {measurement.guardrail_metrics.map((metric) => (
              <li key={metric.metric_id}>
                <strong>{metric.name}</strong>
                <p>{metric.definition}</p>
              </li>
            ))}
          </ul>
        </article>
      </section>

      <section className="stack">
        <h3>Hypothesis backlog</h3>
        {hypotheses.map((hyp) => (
          <article key={hyp.hypothesis_id} className="panel">
            <div className="card-meta">
              <span className="chip soft">{hyp.hypothesis_id}</span>
              <span className="chip">rank {hyp.priority_rank}</span>
              <span className={`chip ${hyp.confidence}`}>{hyp.confidence}</span>
            </div>
            <p>{hyp.hypothesis}</p>
            <p>
              <strong>Intervention:</strong> {hyp.proposed_intervention}
            </p>
            <p>
              <strong>Primary metric:</strong> {hyp.primary_metric}
            </p>
            <p className="muted small">
              Guardrails: {(hyp.guardrail_metrics || []).join(', ')}
            </p>
          </article>
        ))}
      </section>

      {handoffQuery.data?.format === 'markdown' && (
        <section className="panel">
          <h3>Growth handoff excerpt</h3>
          <pre className="markdown-preview">
            {String(handoffQuery.data.content).slice(0, 1800)}
            {String(handoffQuery.data.content).length > 1800 ? '\n…' : ''}
          </pre>
        </section>
      )}
    </div>
  )
}
