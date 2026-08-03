import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { BiasBanner, ErrorState, LoadingState, pretty } from '../components/ui'

export function DiscoveryJourneyPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['explore-journey'],
    queryFn: api.exploreJourney,
  })

  if (isLoading) return <LoadingState label="Loading discovery journey…" />
  if (error || !data) return <ErrorState message={(error as Error)?.message || 'Unknown error'} />

  const signals = data.behaviour_signals

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h2>Discovery Journey</h2>
          <p className="lede">
            How a shopper moves from mission to discovery to blocked exploration.
          </p>
        </div>
      </div>

      <BiasBanner notes={data.bias_notes} />

      <section className="metric-row">
        <article className="metric">
          <span>Habit-driven</span>
          <strong>{signals.habit_pct}%</strong>
          <em>{signals.habit_count} reviews</em>
        </article>
        <article className="metric">
          <span>Experimenting</span>
          <strong>{signals.experimentation_pct}%</strong>
          <em>{signals.experimentation_count} reviews</em>
        </article>
        <article className="metric">
          <span>Urgency context</span>
          <strong>{signals.urgency_pct}%</strong>
          <em>need it now</em>
        </article>
        <article className="metric">
          <span>Convenience driven</span>
          <strong>{signals.convenience_pct}%</strong>
          <em>speed over exploration</em>
        </article>
      </section>

      <section className="journey">
        {data.stages.map((stage, index) => {
          const top = stage.items[0]?.count || 1
          return (
            <article key={stage.stage} className="panel journey-stage">
              <div className="journey-index">{index + 1}</div>
              <div className="journey-body">
                <h3>{stage.stage}</h3>
                <p className="muted small">{stage.description}</p>
                <ul className="bar-list">
                  {stage.items.map((item) => (
                    <li key={item.name}>
                      <span>{pretty(item.name)}</span>
                      <div className="bar-track">
                        <div
                          className="bar-fill"
                          style={{ width: `${(item.count / top) * 100}%` }}
                        />
                      </div>
                      <strong>{item.count}</strong>
                    </li>
                  ))}
                  {!stage.items.length && <li className="muted small">No labels captured yet.</li>}
                </ul>
              </div>
            </article>
          )
        })}
      </section>

      <p className="muted small">Derived from {data.analyzed_records} enriched reviews.</p>
    </div>
  )
}
