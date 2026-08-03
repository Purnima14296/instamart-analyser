import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { BiasBanner, EmptyState, ErrorState, LoadingState, pretty } from '../components/ui'

export function DiscoveryChallengesPage() {
  const [confidence, setConfidence] = useState('')
  const { data, isLoading, error } = useQuery({
    queryKey: ['explore-challenges'],
    queryFn: api.exploreChallenges,
  })

  if (isLoading) return <LoadingState label="Loading discovery challenges…" />
  if (error || !data) return <ErrorState message={(error as Error)?.message || 'Unknown error'} />

  const challenges = data.challenges.filter((c) => !confidence || c.confidence === confidence)

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h2>Discovery Challenges</h2>
          <p className="lede">
            What stops Instamart shoppers from exploring categories beyond their usual basket.
          </p>
        </div>
        <select value={confidence} onChange={(e) => setConfidence(e.target.value)}>
          <option value="">All confidence</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
      </div>

      <BiasBanner notes={data.bias_notes} />

      <section className="split-grid">
        <article className="panel">
          <h3>Barrier frequency</h3>
          <ul className="bar-list">
            {data.barrier_totals.map((row) => (
              <li key={row.name}>
                <span>{pretty(row.name)}</span>
                <div className="bar-track">
                  <div
                    className="bar-fill"
                    style={{
                      width: `${(row.count / (data.barrier_totals[0]?.count || 1)) * 100}%`,
                    }}
                  />
                </div>
                <strong>{row.count}</strong>
              </li>
            ))}
          </ul>
        </article>

        <article className="panel">
          <h3>How shoppers discover today</h3>
          <ul className="bar-list">
            {data.discovery_channels.map((row) => (
              <li key={row.name}>
                <span>{pretty(row.name)}</span>
                <div className="bar-track">
                  <div
                    className="bar-fill alt"
                    style={{
                      width: `${(row.count / (data.discovery_channels[0]?.count || 1)) * 100}%`,
                    }}
                  />
                </div>
                <strong>{row.count}</strong>
              </li>
            ))}
          </ul>
        </article>
      </section>

      {!challenges.length && <EmptyState message="No challenges at this confidence level." />}

      <section className="stack">
        {challenges.map((challenge) => (
          <article key={challenge.theme} className="panel">
            <div className="card-meta">
              <span className={`chip ${challenge.confidence}`}>{challenge.confidence}</span>
              <span className="chip soft">{pretty(challenge.affected_segment)}</span>
              <span className="chip soft">{challenge.supporting_review_count} reviews</span>
            </div>
            <h3>{pretty(challenge.theme)}</h3>
            {Boolean(challenge.category_exploration_barrier?.length) && (
              <p className="muted small">
                Exploration barriers: {challenge.category_exploration_barrier?.map(pretty).join(', ')}
              </p>
            )}
            {challenge.product_opportunity && (
              <p className="callout">Opportunity: {challenge.product_opportunity}</p>
            )}
            {Boolean(challenge.evidence_examples?.length) && (
              <details>
                <summary>{challenge.evidence_examples?.length} evidence quotes</summary>
                <ul className="evidence-list">
                  {challenge.evidence_examples?.map((item) => (
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
    </div>
  )
}
