import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { EmptyState, ErrorState, LoadingState, SectionLabel, pretty } from '../components/ui'

export function OpportunitiesPage() {
  const [typeFilter, setTypeFilter] = useState('all')
  const { data, isLoading, error } = useQuery({
    queryKey: ['opportunities'],
    queryFn: api.opportunities,
  })

  const items = useMemo(() => {
    const list = data?.opportunities || []
    if (typeFilter === 'all') return list
    return list.filter((item) => item.opportunity_types?.includes(typeFilter))
  }, [data, typeFilter])

  if (isLoading) return <LoadingState label="Loading opportunities…" />
  if (error || !data) return <ErrorState message={(error as Error)?.message || 'Unknown error'} />

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h2>Opportunities</h2>
          <p className="lede">Product opportunity areas mapped from validated insights.</p>
        </div>
      </div>

      <div className="filters">
        <label>
          Type
          <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}>
            <option value="all">All</option>
            <option value="trust">Trust</option>
            <option value="discovery">Discovery</option>
            <option value="pricing">Pricing</option>
            <option value="assortment">Assortment</option>
            <option value="service">Service</option>
          </select>
        </label>
      </div>

      {!items.length ? (
        <EmptyState message="No opportunities in this filter." />
      ) : (
        <div className="stack">
          {items.map((opp) => (
            <article key={opp.opportunity_id} className="panel opportunity">
              <div className="card-meta">
                <span className={`chip ${opp.priority.priority_band}`}>
                  {opp.priority.priority_band} · {opp.priority.score}
                </span>
                {(opp.opportunity_types || []).map((type) => (
                  <span key={type} className="chip soft">
                    {type}
                  </span>
                ))}
              </div>
              <h3>
                #{opp.rank ?? '—'} {opp.title}
              </h3>
              <div className="triptych compact">
                <div>
                  <SectionLabel>User problem</SectionLabel>
                  <p>{opp.user_problem}</p>
                </div>
                <div>
                  <SectionLabel>Interpretation</SectionLabel>
                  <p>{opp.opportunity_statement}</p>
                  <p className="muted small">
                    {pretty(opp.affected_segment)} · {pretty(opp.shopping_mission)} ·{' '}
                    {opp.supporting_record_count} reviews
                  </p>
                </div>
                <div>
                  <SectionLabel>Recommended moves</SectionLabel>
                  <ul>
                    {(opp.recommended_moves || []).map((move) => (
                      <li key={move}>{move}</li>
                    ))}
                  </ul>
                </div>
              </div>
              {opp.evidence_examples?.[0] && (
                <blockquote>“{opp.evidence_examples[0].snippet}”</blockquote>
              )}
            </article>
          ))}
        </div>
      )}
    </div>
  )
}
