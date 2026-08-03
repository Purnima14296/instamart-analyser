import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { BiasBanner, ErrorState, LoadingState, pretty } from '../components/ui'

function pairList(pairs?: [string, number][]) {
  if (!pairs?.length) return '—'
  return pairs.map(([name, count]) => `${pretty(name)} (${count})`).join(', ')
}

export function SegmentExplorerPage() {
  const [selected, setSelected] = useState<string | null>(null)
  const { data, isLoading, error } = useQuery({
    queryKey: ['explore-segments'],
    queryFn: api.exploreSegments,
  })

  if (isLoading) return <LoadingState label="Loading segments…" />
  if (error || !data) return <ErrorState message={(error as Error)?.message || 'Unknown error'} />

  const active = data.segments.find((s) => s.segment === selected) || data.segments[0]

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h2>Segment Explorer</h2>
          <p className="lede">
            {data.segment_count} shopper segments ranked by discovery friction and volume.
          </p>
        </div>
      </div>

      <BiasBanner notes={data.bias_notes} />

      {data.recommended_focus && (
        <section className="panel highlight">
          <p className="section-label">Recommended focus segment</p>
          <h3>{pretty(data.recommended_focus.segment)}</h3>
          <p>
            {data.recommended_focus.review_count} reviews · priority score{' '}
            {data.recommended_focus.priority_score} · discovery barrier rate{' '}
            {data.recommended_focus.discovery_barrier_rate}%
          </p>
          <p className="muted small">{data.formula}</p>
        </section>
      )}

      <section className="explorer-grid">
        <div className="explorer-list">
          {data.segments.map((segment) => (
            <button
              key={segment.segment}
              className={`explorer-item ${active?.segment === segment.segment ? 'active' : ''}`}
              onClick={() => setSelected(segment.segment)}
            >
              <strong>{pretty(segment.segment)}</strong>
              <span className="muted small">{segment.review_count} reviews</span>
              {segment.priority && (
                <span className="chip soft">score {segment.priority.priority_score}</span>
              )}
            </button>
          ))}
        </div>

        {active && (
          <article className="panel">
            <h3>{pretty(active.segment)}</h3>
            <div className="card-meta">
              <span className="chip soft">{active.review_count} reviews</span>
              {active.priority && (
                <span className="chip soft">
                  priority {active.priority.priority_score} · discovery barrier{' '}
                  {active.priority.discovery_barrier_rate}%
                </span>
              )}
            </div>
            <div className="kv-grid">
              <div>
                <h4>Top missions</h4>
                <p>{pairList(active.top_missions)}</p>
              </div>
              <div>
                <h4>Top barriers</h4>
                <p>{pairList(active.top_barriers)}</p>
              </div>
              <div>
                <h4>Discovery barriers</h4>
                <p>{pairList(active.top_discovery_barriers)}</p>
              </div>
              <div>
                <h4>Experimentation likelihood</h4>
                <p>{pairList(active.experimentation_likelihood)}</p>
              </div>
            </div>
          </article>
        )}
      </section>

      <section className="panel">
        <h3>Segment priority table</h3>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Segment</th>
                <th>Reviews</th>
                <th>Discovery barrier rate</th>
                <th>Trust barrier rate</th>
                <th>Priority score</th>
              </tr>
            </thead>
            <tbody>
              {data.segments.map((row) => (
                <tr key={row.segment} className={row.priority?.recommended ? 'recommended-row' : ''}>
                  <td>{pretty(row.segment)}</td>
                  <td>{row.review_count}</td>
                  <td>
                    {row.priority ? `${row.priority.discovery_barrier_rate}%` : '—'}
                  </td>
                  <td>{row.priority ? `${row.priority.trust_barrier_rate}%` : '—'}</td>
                  <td>{row.priority?.priority_score ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
