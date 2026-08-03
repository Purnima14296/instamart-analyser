import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { BiasBanner, EmptyState, ErrorState, LoadingState, pretty } from '../components/ui'

export function UnmetNeedsPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['explore-unmet-needs'],
    queryFn: api.exploreUnmetNeeds,
  })

  if (isLoading) return <LoadingState label="Loading unmet needs…" />
  if (error || !data) return <ErrorState message={(error as Error)?.message || 'Unknown error'} />

  const top = data.needs[0]?.mentions || 1

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h2>Unmet Needs</h2>
          <p className="lede">
            Information gaps and assortment gaps shoppers name but Instamart doesn’t answer.
          </p>
        </div>
      </div>

      <BiasBanner notes={data.bias_notes} />

      {!data.needs.length && (
        <EmptyState message="No information or assortment gaps labelled yet. Run enrichment to populate." />
      )}

      <section className="stack">
        {data.needs.map((need) => (
          <article key={need.need} className="panel">
            <div className="card-meta">
              <span className={`chip ${need.confidence}`}>{need.confidence}</span>
              <span className="chip soft">{need.mentions} mentions</span>
            </div>
            <h3>{pretty(need.need)}</h3>
            <div className="bar-track wide">
              <div className="bar-fill alt" style={{ width: `${(need.mentions / top) * 100}%` }} />
            </div>
            <p className="muted small">
              Segments: {need.top_segments.map((s) => `${pretty(s.name)} (${s.count})`).join(', ') || '—'}
            </p>
            {Boolean(need.evidence.length) && (
              <details>
                <summary>Evidence</summary>
                <ul className="evidence-list">
                  {need.evidence.map((item) => (
                    <li key={item.record_id}>
                      <span className="chip soft">{pretty(item.source)}</span>
                      <p>{item.snippet}</p>
                    </li>
                  ))}
                </ul>
              </details>
            )}
          </article>
        ))}
      </section>

      {Boolean(data.linked_opportunities.length) && (
        <section className="panel">
          <h3>Where these needs land in the roadmap</h3>
          <ul className="link-list">
            {data.linked_opportunities.map((opp) => (
              <li key={opp.opportunity_id}>
                <Link to="/opportunities">{opp.title}</Link>
                <span className="chip soft">{opp.priority_band}</span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  )
}
