import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { EmptyState, ErrorState, LoadingState, pretty } from '../components/ui'

const PAGE_SIZE = 25

export function ReviewDiscoveryPage() {
  const [q, setQ] = useState('')
  const [source, setSource] = useState('')
  const [sentiment, setSentiment] = useState('')
  const [segment, setSegment] = useState('')
  const [barrier, setBarrier] = useState('')
  const [enrichedOnly, setEnrichedOnly] = useState(false)
  const [page, setPage] = useState(0)

  const { data, isLoading, error } = useQuery({
    queryKey: ['explore-reviews', q, source, sentiment, segment, barrier, enrichedOnly, page],
    queryFn: () =>
      api.exploreReviews({
        q: q || undefined,
        source: source || undefined,
        sentiment: sentiment || undefined,
        segment: segment || undefined,
        barrier: barrier || undefined,
        enriched_only: enrichedOnly || undefined,
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
      }),
  })

  if (isLoading && !data) return <LoadingState label="Loading reviews…" />
  if (error) return <ErrorState message={(error as Error).message} />

  const facets = data?.facets
  const total = data?.total_matched ?? 0
  const maxPage = Math.max(0, Math.ceil(total / PAGE_SIZE) - 1)

  const reset = (fn: (v: string) => void) => (value: string) => {
    fn(value)
    setPage(0)
  }

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h2>Review Discovery</h2>
          <p className="lede">Search every ingested review and inspect its AI labels.</p>
        </div>
      </div>

      <section className="panel">
        <div className="filter-grid">
          <input
            placeholder="Search review text…"
            value={q}
            onChange={(e) => reset(setQ)(e.target.value)}
          />
          <select value={source} onChange={(e) => reset(setSource)(e.target.value)}>
            <option value="">All sources</option>
            {facets?.sources.map((s) => (
              <option key={s} value={s}>
                {pretty(s)}
              </option>
            ))}
          </select>
          <select value={sentiment} onChange={(e) => reset(setSentiment)(e.target.value)}>
            <option value="">All sentiment</option>
            {facets?.sentiments.map((s) => (
              <option key={s} value={s}>
                {pretty(s)}
              </option>
            ))}
          </select>
          <select value={segment} onChange={(e) => reset(setSegment)(e.target.value)}>
            <option value="">All segments</option>
            {facets?.segments.map((s) => (
              <option key={s} value={s}>
                {pretty(s)}
              </option>
            ))}
          </select>
          <select value={barrier} onChange={(e) => reset(setBarrier)(e.target.value)}>
            <option value="">All barriers</option>
            {facets?.barriers.map((s) => (
              <option key={s} value={s}>
                {pretty(s)}
              </option>
            ))}
          </select>
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={enrichedOnly}
              onChange={(e) => {
                setEnrichedOnly(e.target.checked)
                setPage(0)
              }}
            />
            Enriched only
          </label>
        </div>
        <p className="muted small">
          {total.toLocaleString()} matching reviews · showing {data?.returned ?? 0}
        </p>
      </section>

      {!data?.reviews.length && <EmptyState message="No reviews match these filters." />}

      <section className="stack">
        {data?.reviews.map((review) => (
          <article key={review.record_id} className="panel">
            <div className="card-meta">
              <span className="chip soft">{pretty(review.source)}</span>
              {review.rating != null && <span className="chip soft">{review.rating}★</span>}
              {review.sentiment && (
                <span className={`chip ${review.sentiment}`}>{pretty(review.sentiment)}</span>
              )}
              {review.user_segment && (
                <span className="chip soft">{pretty(review.user_segment)}</span>
              )}
              {!review.enriched && <span className="chip low">not enriched</span>}
            </div>
            {review.title && <p className="opportunity-title">{review.title}</p>}
            <p>{review.body_text}</p>
            {Boolean(review.barriers.length) && (
              <p className="muted small">Barriers: {review.barriers.map(pretty).join(', ')}</p>
            )}
            {Boolean(review.categories_mentioned.length) && (
              <p className="muted small">
                Categories: {review.categories_mentioned.map(pretty).join(', ')}
              </p>
            )}
            {review.url && (
              <a className="ghost-link" href={review.url} target="_blank" rel="noreferrer">
                Open source →
              </a>
            )}
          </article>
        ))}
      </section>

      {total > PAGE_SIZE && (
        <div className="button-row">
          <button
            className="secondary"
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0}
          >
            Previous
          </button>
          <span className="muted small">
            Page {page + 1} of {maxPage + 1}
          </span>
          <button
            className="secondary"
            onClick={() => setPage((p) => Math.min(maxPage, p + 1))}
            disabled={page >= maxPage}
          >
            Next
          </button>
        </div>
      )}
    </div>
  )
}
