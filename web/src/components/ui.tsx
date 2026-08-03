import type { ReactNode } from 'react'

export function LoadingState({ label = 'Loading…' }: { label?: string }) {
  return <div className="state-box">{label}</div>
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="state-box error">
      <strong>Couldn’t load this view</strong>
      <p>{message}</p>
      <p className="muted small">
        Check that the API is running on port 8000 and your role token is valid.
      </p>
    </div>
  )
}

export function EmptyState({ message }: { message: string }) {
  return <div className="state-box muted">{message}</div>
}

export function BiasBanner({ notes, sampleSize }: { notes: string[]; sampleSize?: number }) {
  if (!notes?.length && sampleSize == null) return null
  return (
    <aside className="bias-banner">
      <strong>Read with care</strong>
      {sampleSize != null && <p>Current enriched sample: {sampleSize} reviews</p>}
      <ul>
        {notes.map((note) => (
          <li key={note}>{note}</li>
        ))}
      </ul>
    </aside>
  )
}

export function SectionLabel({ children }: { children: ReactNode }) {
  return <p className="section-label">{children}</p>
}

export function pretty(value?: string) {
  if (!value) return '—'
  return value.replaceAll('_', ' ')
}
