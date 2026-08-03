import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { BiasBanner, ErrorState, LoadingState, pretty } from '../components/ui'

export function RootCauseAnalysisPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['explore-root-causes'],
    queryFn: api.exploreRootCauses,
  })

  if (isLoading) return <LoadingState label="Loading root causes…" />
  if (error || !data) return <ErrorState message={(error as Error)?.message || 'Unknown error'} />

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h2>Root Cause Analysis</h2>
          <p className="lede">
            For each barrier, the underlying concerns shoppers actually describe.
          </p>
        </div>
      </div>

      <BiasBanner notes={data.bias_notes} />

      <section className="panel">
        <p className="section-label">Method</p>
        <p>{data.method}</p>
        <p className="muted small">
          {data.analyzed_records} enriched records · {data.cause_group_count} barrier groups
        </p>
      </section>

      <section className="stack">
        {data.causes.map((cause) => {
          const top = cause.root_causes[0]?.count || 1
          return (
            <article key={cause.barrier} className="panel">
              <div className="card-meta">
                <span className={`chip ${cause.confidence}`}>{cause.confidence} confidence</span>
                <span className="chip soft">{cause.affected_reviews} reviews</span>
                {cause.top_segments[0] && (
                  <span className="chip soft">{pretty(cause.top_segments[0].name)}</span>
                )}
              </div>
              <h3>{pretty(cause.barrier)}</h3>

              <h4>Contributing causes</h4>
              <ul className="bar-list">
                {cause.root_causes.map((row) => (
                  <li key={row.name}>
                    <span>{row.name}</span>
                    <div className="bar-track">
                      <div className="bar-fill" style={{ width: `${(row.count / top) * 100}%` }} />
                    </div>
                    <strong>{row.count}</strong>
                  </li>
                ))}
                {!cause.root_causes.length && (
                  <li className="muted small">
                    No structured concern labels captured for this barrier yet.
                  </li>
                )}
              </ul>

              <div className="kv-grid">
                <div>
                  <h4>Segments hit</h4>
                  <p>
                    {cause.top_segments.map((s) => `${pretty(s.name)} (${s.count})`).join(', ') ||
                      '—'}
                  </p>
                </div>
                <div>
                  <h4>Missions affected</h4>
                  <p>
                    {cause.top_missions.map((s) => `${pretty(s.name)} (${s.count})`).join(', ') ||
                      '—'}
                  </p>
                </div>
                <div>
                  <h4>Sentiment mix</h4>
                  <p>
                    {Object.entries(cause.sentiment)
                      .map(([k, v]) => `${pretty(k)} ${v}`)
                      .join(' · ') || '—'}
                  </p>
                </div>
              </div>

              {Boolean(cause.evidence.length) && (
                <details>
                  <summary>Evidence</summary>
                  <ul className="evidence-list">
                    {cause.evidence.map((item) => (
                      <li key={item.record_id}>
                        <span className="chip soft">{pretty(item.source)}</span>
                        <p>{item.snippet}</p>
                      </li>
                    ))}
                  </ul>
                </details>
              )}
            </article>
          )
        })}
      </section>
    </div>
  )
}
