import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { BiasBanner, ErrorState, LoadingState, pretty } from '../components/ui'

export function ValidationPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['explore-validation'],
    queryFn: api.exploreValidation,
  })

  if (isLoading) return <LoadingState label="Loading validation…" />
  if (error || !data) return <ErrorState message={(error as Error)?.message || 'Unknown error'} />

  const refinementGroups = [
    { label: 'Prompt refinements', rows: data.refinements.prompt },
    { label: 'Taxonomy refinements', rows: data.refinements.taxonomy },
    { label: 'Threshold refinements', rows: data.refinements.threshold },
  ]

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h2>Validation</h2>
          <p className="lede">
            Do the AI-enriched themes agree with keyword pre-analysis, and is this pilot-ready?
          </p>
        </div>
      </div>

      <BiasBanner notes={data.bias_notes} />

      <section className="metric-row">
        <article className="metric">
          <span>Pilot ready</span>
          <strong>{data.pilot_ready ? 'Yes' : 'No'}</strong>
          <em>Phase 5 gate</em>
        </article>
        <article className="metric">
          <span>Top-5 alignment</span>
          <strong>{data.aligned_top5_count ?? 0}/5</strong>
          <em>keyword vs AI</em>
        </article>
        <article className="metric">
          <span>Open defects</span>
          <strong>{data.open_defects ?? 0}</strong>
          <em>from stakeholder review</em>
        </article>
        <article className="metric">
          <span>Feedback captured</span>
          <strong>{data.stakeholder_feedback_count || data.feedback_responses || 0}</strong>
          <em>responses logged</em>
        </article>
      </section>

      <section className="panel highlight">
        <p className="section-label">Verdict</p>
        <h3>{data.alignment_verdict || 'Not yet computed'}</h3>
        <p className="muted small">{data.method}</p>
      </section>

      <section className="panel">
        <h3>Keyword vs AI barrier ranking</h3>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Barrier</th>
                <th>Keyword count</th>
                <th>AI count</th>
                <th>Keyword rank</th>
                <th>AI rank</th>
                <th>Aligned</th>
              </tr>
            </thead>
            <tbody>
              {data.comparisons.map((row) => (
                <tr key={row.barrier}>
                  <td>{pretty(row.barrier)}</td>
                  <td>{row.pre_llm_mapped_count}</td>
                  <td>{row.ai_enriched_count}</td>
                  <td>{row.pre_llm_rank ?? '—'}</td>
                  <td>{row.ai_rank ?? '—'}</td>
                  <td>
                    <span className={`chip ${row.aligned_in_top5 ? 'high' : 'low'}`}>
                      {row.aligned_in_top5 ? 'aligned' : 'divergent'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="split-grid">
        {refinementGroups.map((group) => (
          <article key={group.label} className="panel">
            <h3>{group.label}</h3>
            {group.rows.length ? (
              <ul className="link-list">
                {group.rows.map((row, index) => (
                  <li key={index}>
                    <span>{String(row.change || row.description || JSON.stringify(row))}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="muted small">None logged.</p>
            )}
          </article>
        ))}
      </section>
    </div>
  )
}
