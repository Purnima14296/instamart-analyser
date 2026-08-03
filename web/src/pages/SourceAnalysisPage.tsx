import { useQuery } from '@tanstack/react-query'
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from '../api/client'
import { BiasBanner, ErrorState, LoadingState, pretty } from '../components/ui'
import { useChartColors } from '../theme/ThemeContext'

export function SourceAnalysisPage() {
  const colors = useChartColors()
  const { data, isLoading, error } = useQuery({
    queryKey: ['explore-sources'],
    queryFn: api.exploreSources,
  })

  if (isLoading) return <LoadingState label="Loading source analysis…" />
  if (error || !data) return <ErrorState message={(error as Error)?.message || 'Unknown error'} />

  const chartData = data.sources.map((s) => ({ name: pretty(s.source), count: s.count }))
  const ratingData = Object.entries(data.rating_distribution).map(([star, count]) => ({
    name: `${star}★`,
    count,
  }))

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h2>Source Analysis</h2>
          <p className="lede">Where Instamart feedback comes from, and how each channel skews.</p>
        </div>
      </div>

      <BiasBanner notes={data.bias_notes} />

      <section className="metric-row">
        <article className="metric">
          <span>Total reviews</span>
          <strong>{data.total_reviews.toLocaleString()}</strong>
          <em>normalized</em>
        </article>
        <article className="metric">
          <span>Sources</span>
          <strong>{data.source_count}</strong>
          <em>channels ingested</em>
        </article>
        <article className="metric">
          <span>Largest source</span>
          <strong>{pretty(data.sources[0]?.source)}</strong>
          <em>{data.sources[0]?.share_pct}% of corpus</em>
        </article>
        <article className="metric">
          <span>Enriched</span>
          <strong>{data.sources.reduce((acc, s) => acc + s.enriched_count, 0)}</strong>
          <em>AI-labelled reviews</em>
        </article>
      </section>

      <section className="split-grid">
        <article className="panel">
          <h3>Volume by source</h3>
          <div className="chart-wrap">
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={chartData} layout="vertical" margin={{ left: 24, right: 12 }}>
                <XAxis type="number" hide />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={110}
                  tick={{ fontSize: 12, fill: colors.axis }}
                />
                <Tooltip
                  cursor={{ fill: colors.tooltipLine }}
                  contentStyle={{
                    background: colors.tooltipBg,
                    border: `1px solid ${colors.tooltipLine}`,
                    borderRadius: 12,
                  }}
                />
                <Bar dataKey="count" fill={colors.accent} radius={[0, 6, 6, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </article>

        <article className="panel">
          <h3>Rating distribution</h3>
          <div className="chart-wrap">
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={ratingData}>
                <XAxis dataKey="name" tick={{ fontSize: 12, fill: colors.axis }} />
                <YAxis tick={{ fontSize: 12, fill: colors.axis }} />
                <Tooltip
                  cursor={{ fill: colors.tooltipLine }}
                  contentStyle={{
                    background: colors.tooltipBg,
                    border: `1px solid ${colors.tooltipLine}`,
                    borderRadius: 12,
                  }}
                />
                <Bar dataKey="count" fill={colors.accent2} radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <p className="muted small">{data.coverage_note}</p>
        </article>
      </section>

      <section className="panel">
        <h3>Source breakdown</h3>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Source</th>
                <th>Reviews</th>
                <th>Share</th>
                <th>Avg rating</th>
                <th>Enriched</th>
                <th>Negative %</th>
                <th>Top barrier</th>
              </tr>
            </thead>
            <tbody>
              {data.sources.map((row) => (
                <tr key={row.source}>
                  <td>{pretty(row.source)}</td>
                  <td>{row.count}</td>
                  <td>{row.share_pct}%</td>
                  <td>{row.avg_rating ?? '—'}</td>
                  <td>
                    {row.enriched_count} ({row.enriched_pct}%)
                  </td>
                  <td>{row.sentiment_pct.negative}%</td>
                  <td>{pretty(row.top_barriers[0]?.name) || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
