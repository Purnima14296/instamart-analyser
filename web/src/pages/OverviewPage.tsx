import { useQuery } from '@tanstack/react-query'
import { Bar, BarChart, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { BiasBanner, ErrorState, LoadingState, pretty } from '../components/ui'
import { useChartColors } from '../theme/ThemeContext'

export function OverviewPage() {
  const colors = useChartColors()
  const sentimentColors: Record<string, string> = {
    positive: colors.positive,
    negative: colors.negative,
    neutral: colors.neutral,
    mixed: colors.mixed,
  }
  const overviewQuery = useQuery({
    queryKey: ['overview'],
    queryFn: api.overview,
  })
  const researchQuery = useQuery({
    queryKey: ['research-summary'],
    queryFn: api.researchSummary,
  })

  if (overviewQuery.isLoading || researchQuery.isLoading) {
    return <LoadingState label="Loading research overview…" />
  }
  if (overviewQuery.error || !overviewQuery.data) {
    return <ErrorState message={(overviewQuery.error as Error)?.message || 'Unknown error'} />
  }
  if (researchQuery.error || !researchQuery.data) {
    return <ErrorState message={(researchQuery.error as Error)?.message || 'Research summary failed'} />
  }

  const data = overviewQuery.data
  const research = researchQuery.data
  const barriers = (data.theme_summary.top_barriers || []).map(([name, count]) => ({
    name: pretty(name),
    count,
  }))
  const sentimentPie = Object.entries(research.sentiment.percentages).map(([name, value]) => ({
    name,
    value,
  }))
  const focus = research.segment_priority.recommended_focus
  const pipeline = research.pipeline_status

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <p className="eyebrow">Instamart · Product Research Intelligence</p>
          <h2>Category Discovery Research</h2>
          <p className="lede">{research.subtitle}</p>
        </div>
        <div className={`pilot-badge ${data.pilot.pilot_ready ? 'ready' : 'not-ready'}`}>
          {data.pilot.pilot_ready ? 'Pilot ready' : 'Pilot not ready'}
        </div>
      </div>

      <BiasBanner notes={data.bias_notes || research.bias_notes || []} sampleSize={data.sample_size} />

      {data.enrichment.quota_blocked && (
        <aside className="bias-banner">
          <strong>Enrichment paused</strong>
          <p>{data.enrichment.quota_message}</p>
        </aside>
      )}

      <section className="status-strip">
        <div>
          <span>Ingested</span>
          <strong>{research.portfolio.reviews_ingested.toLocaleString()}</strong>
          <em>
            Play {research.portfolio.play_store} · App {research.portfolio.app_store} · Reddit{' '}
            {research.portfolio.reddit}
          </em>
        </div>
        <div>
          <span>Analyzed</span>
          <strong>
            {research.portfolio.analysis_sample}/{research.portfolio.cohort_size}
          </strong>
          <em>{research.portfolio.analysis_pending} pending</em>
        </div>
        <div>
          <span>Last pipeline</span>
          <strong>{pipeline.last_job?.job_type || '—'}</strong>
          <em>
            {pipeline.active_job
              ? `active: ${pipeline.active_job.status}`
              : pipeline.last_job?.status || 'idle'}
          </em>
        </div>
        <div>
          <span>Discovery trust</span>
          <strong>{research.discovery_trust.score}/100</strong>
          <em>{research.discovery_trust.label}</em>
        </div>
      </section>

      <section className="panel research-hero">
        <h3>AI Executive Summary</h3>
        <p className="executive-brief">{research.executive_brief}</p>
        <div className="grounding-row">
          Grounded in {research.research_grounding.themes} themes ·{' '}
          {research.research_grounding.segments} segments · {research.research_grounding.insights}{' '}
          insights · {research.research_grounding.opportunities} opportunities
        </div>
        <ul className="finding-list">
          {research.key_findings.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </section>

      <section className="metric-row">
        <article className="metric">
          <span>Reviews ingested</span>
          <strong>{research.portfolio.reviews_ingested.toLocaleString()}</strong>
          <em>normalized store</em>
        </article>
        <article className="metric">
          <span>Themes discovered</span>
          <strong>{research.portfolio.themes_discovered}</strong>
          <em>{research.portfolio.insights_count} insights</em>
        </article>
        <article className="metric">
          <span>Avg rating</span>
          <strong>{research.portfolio.avg_rating ?? '—'}★</strong>
          <em>from rating distribution</em>
        </article>
        <article className="metric">
          <span>Analysis sample</span>
          <strong>{research.portfolio.analysis_sample}</strong>
          <em>{research.portfolio.analysis_pending} pending</em>
        </article>
      </section>

      <section className="metric-row">
        <article className="metric">
          <span>Enriched coverage</span>
          <strong>
            {data.enrichment.enriched_count}/{data.enrichment.cohort_size}
          </strong>
          <em>{data.enrichment.coverage_pct}%</em>
        </article>
        <article className="metric">
          <span>Insights</span>
          <strong>{data.insights.insight_count}</strong>
          <em>{data.insights.dry_run ? 'dry-run drafts' : 'live drafts'}</em>
        </article>
        <article className="metric">
          <span>Opportunities</span>
          <strong>{data.opportunities.opportunity_count}</strong>
          <em>{data.opportunities.hypothesis_count} hypotheses</em>
        </article>
        <article className="metric">
          <span>Quota left today</span>
          <strong>{data.enrichment.usage_today.remaining_enrichment_estimate}</strong>
          <em>enrichment slots</em>
        </article>
      </section>

      <section className="split-grid">
        <article className="panel">
          <h3>Top opportunity</h3>
          {research.top_opportunity ? (
            <>
              <p className="opportunity-title">{research.top_opportunity.title}</p>
              <p className="muted">{research.top_opportunity.opportunity_statement}</p>
              <div className="card-meta">
                <span className="chip soft">{research.top_opportunity.priority_band}</span>
                <span className="chip soft">
                  score {research.top_opportunity.priority_score}
                </span>
                <span className="chip soft">
                  {pretty(research.top_opportunity.affected_segment || '')}
                </span>
              </div>
              <Link className="ghost-link" to="/opportunities">
                Open opportunity map →
              </Link>
            </>
          ) : (
            <p className="muted">No opportunities yet. Run Phase 4.</p>
          )}
        </article>

        <article className="panel">
          <h3>Research highlights</h3>
          <p>
            <strong>Top challenge:</strong> {pretty(research.top_challenge.name)} (
            {research.top_challenge.count})
          </p>
          <p className="muted small">{research.top_challenge.detail}</p>
          <p>
            <strong>Most affected segment:</strong>{' '}
            {focus ? pretty(focus.segment) : '—'}
            {focus ? ` (priority ${focus.priority_score})` : ''}
          </p>
          <p>
            <strong>Discovery trust:</strong> {research.discovery_trust.score}/100
          </p>
          {focus && (
            <p className="muted small">
              Recommended focus: {pretty(focus.segment)} · {focus.review_count} reviews · top
              frustration {pretty(focus.top_frustration || 'n/a')}
            </p>
          )}
        </article>
      </section>

      <section className="split-grid">
        <article className="panel">
          <h3>Sentiment breakdown</h3>
          <div className="chart-wrap sentiment-chart">
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={sentimentPie} dataKey="value" nameKey="name" innerRadius={55} outerRadius={85}>
                  {sentimentPie.map((entry) => (
                    <Cell key={entry.name} fill={sentimentColors[entry.name] || colors.neutral} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(value) => `${value ?? 0}%`}
                  contentStyle={{
                    background: colors.tooltipBg,
                    border: `1px solid ${colors.tooltipLine}`,
                    borderRadius: 12,
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="sentiment-legend">
            {sentimentPie.map((entry) => (
              <span key={entry.name}>
                <i style={{ background: sentimentColors[entry.name] }} />
                {pretty(entry.name)} {entry.value}%
              </span>
            ))}
          </div>
        </article>

        <article className="panel">
          <h3>Category discovery trust</h3>
          <div className="trust-gauge">
            <strong>{research.discovery_trust.score}</strong>
            <span>/100 · {research.discovery_trust.label}</span>
          </div>
          <p className="muted small">{research.discovery_trust.formula}</p>
          <ul className="mini-stack">
            {Object.entries(research.discovery_trust.components).map(([k, v]) => (
              <li key={k}>
                {pretty(k)}: −{v}
              </li>
            ))}
          </ul>
        </article>
      </section>

      <section className="panel">
        <h3>Segment priority</h3>
        <p className="muted small">{research.segment_priority.formula}</p>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Rank</th>
                <th>Segment</th>
                <th>Reviews</th>
                <th>% Sample</th>
                <th>Discovery rate</th>
                <th>Trust rate</th>
                <th>Priority</th>
                <th>Top frustration</th>
              </tr>
            </thead>
            <tbody>
              {research.segment_priority.segments.map((row) => (
                <tr key={row.segment} className={row.recommended ? 'recommended-row' : undefined}>
                  <td>{row.rank}{row.recommended ? ' ★' : ''}</td>
                  <td>{pretty(row.segment)}</td>
                  <td>{row.review_count}</td>
                  <td>{row.pct_sample}%</td>
                  <td>{row.discovery_barrier_rate}</td>
                  <td>{row.trust_barrier_rate}</td>
                  <td>{row.priority_score}</td>
                  <td>{pretty(row.top_frustration || '—')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="split-grid">
        <article className="panel">
          <h3>Top barriers</h3>
          <div className="chart-wrap">
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={barriers} layout="vertical" margin={{ left: 24, right: 12 }}>
                <XAxis type="number" hide />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={120}
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
          <h3>Where to go next</h3>
          <ul className="action-list">
            <li>
              <Link to="/insights">Review evidence-backed insights</Link>
            </li>
            <li>
              <Link to="/opportunities">Prioritize opportunity areas</Link>
            </li>
            <li>
              <Link to="/experiments">Open experiment backlog</Link>
            </li>
            <li>
              <Link to="/review">Approve draft insights</Link>
            </li>
            <li>
              <Link to="/jobs">Run ingest / analysis pipeline</Link>
            </li>
          </ul>
          <div className="mini-stack">
            <p>
              <strong>Alignment:</strong> {data.pilot.alignment_verdict || '—'}
            </p>
            <p>
              <strong>Top mission:</strong>{' '}
              {pretty(data.theme_summary.top_missions?.[0]?.[0])}
            </p>
            <p>
              <strong>Top segment:</strong>{' '}
              {pretty(data.theme_summary.top_segments?.[0]?.[0])}
            </p>
          </div>
        </article>
      </section>

      <section className="panel">
        <h3>Known limitations</h3>
        <ul>
          {(data.known_limitations || []).map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
        <h4>Operational notes</h4>
        <ul>
          {(data.operational_notes || []).map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </section>
    </div>
  )
}
