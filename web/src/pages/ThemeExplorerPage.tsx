import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { BiasBanner, EmptyState, ErrorState, LoadingState, pretty } from '../components/ui'

export function ThemeExplorerPage() {
  const [barrier, setBarrier] = useState('')
  const [selected, setSelected] = useState<string | null>(null)

  const { data, isLoading, error } = useQuery({
    queryKey: ['themes'],
    queryFn: api.themes,
  })

  if (isLoading) return <LoadingState label="Loading themes…" />
  if (error || !data) return <ErrorState message={(error as Error)?.message || 'Unknown error'} />

  const clusters = (data.clusters || []).filter(
    (c) => !barrier || c.primary_barrier === barrier,
  )
  const active = clusters.find((c) => c.theme_id === selected) || clusters[0]
  const barriers = Array.from(new Set((data.clusters || []).map((c) => c.primary_barrier)))

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h2>Theme Explorer</h2>
          <p className="lede">
            {data.cluster_count ?? clusters.length} themes clustered from{' '}
            {data.enriched_record_count ?? 0} enriched reviews.
          </p>
        </div>
        <select value={barrier} onChange={(e) => setBarrier(e.target.value)}>
          <option value="">All barriers</option>
          {barriers.map((b) => (
            <option key={b} value={b}>
              {pretty(b)}
            </option>
          ))}
        </select>
      </div>

      <BiasBanner notes={data.bias_notes} />

      {!clusters.length && <EmptyState message="No themes match this filter." />}

      <section className="explorer-grid">
        <div className="explorer-list">
          {clusters.map((cluster) => (
            <button
              key={cluster.theme_id}
              className={`explorer-item ${active?.theme_id === cluster.theme_id ? 'active' : ''}`}
              onClick={() => setSelected(cluster.theme_id)}
            >
              <strong>{pretty(cluster.primary_barrier)}</strong>
              <span className="muted small">
                {pretty(cluster.shopping_mission)} · {pretty(cluster.primary_category)}
              </span>
              <span className="chip soft">{cluster.total_supporting_records} reviews</span>
            </button>
          ))}
        </div>

        {active && (
          <article className="panel">
            <h3>{pretty(active.theme_id)}</h3>
            <div className="card-meta">
              <span className="chip soft">{pretty(active.affected_segment)}</span>
              <span className="chip soft">{active.total_supporting_records} reviews</span>
              <span className={`chip ${active.experimentation_likelihood || 'soft'}`}>
                experimentation: {active.experimentation_likelihood || 'unknown'}
              </span>
            </div>

            <div className="kv-grid">
              <div>
                <h4>Exploration barriers</h4>
                <p>{active.category_exploration_barrier?.map(pretty).join(', ') || '—'}</p>
              </div>
              <div>
                <h4>Discovery triggers</h4>
                <p>{active.discovery_trigger?.map(pretty).join(', ') || '—'}</p>
              </div>
              <div>
                <h4>Trust signals needed</h4>
                <p>{active.required_trust_signal?.map(pretty).join(', ') || '—'}</p>
              </div>
              <div>
                <h4>Source mix</h4>
                <p>
                  {Object.entries(active.source_breakdown || {})
                    .map(([k, v]) => `${pretty(k)} ${v}`)
                    .join(' · ') || '—'}
                </p>
              </div>
            </div>

            <h4>Segment breakdown</h4>
            <ul className="bar-list">
              {Object.entries(active.segment_breakdown || {})
                .sort((a, b) => b[1] - a[1])
                .map(([name, count]) => (
                  <li key={name}>
                    <span>{pretty(name)}</span>
                    <div className="bar-track">
                      <div
                        className="bar-fill"
                        style={{
                          width: `${(count / active.total_supporting_records) * 100}%`,
                        }}
                      />
                    </div>
                    <strong>{count}</strong>
                  </li>
                ))}
            </ul>

            {Boolean(active.supporting_evidence?.length) && (
              <details open>
                <summary>Evidence</summary>
                <ul className="evidence-list">
                  {active.supporting_evidence?.map((item) => (
                    <li key={item.record_id}>
                      <span className="chip soft">{pretty(item.source)}</span>
                      <p>{item.snippet}</p>
                    </li>
                  ))}
                </ul>
              </details>
            )}
          </article>
        )}
      </section>
    </div>
  )
}
