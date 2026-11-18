import { useState } from 'react'

const FIELD_LABELS = {
  title: 'Game name',
  starts_at: 'Start time',
  ends_at: 'End time',
  format_label: 'Format',
  game_player_group: 'Player group',
  skill_level: 'Skill level',
  environment_type: 'Environment',
  price_per_player_cents: 'Price per player',
  total_spots: 'Capacity',
  timezone: 'Time zone',
  venue_name_snapshot: 'Venue',
  description: 'Game details',
}

// Plain wording for a request that staff have not finished processing.
const REQUEST_STATUS_TEXT = {
  pending: 'waiting for staff',
  processing: 'being processed',
  failed: 'being retried',
}

function displayValue(field, value, timeZone) {
  if (value === null || value === undefined || value === '') return 'Not set'
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  if (field === 'price_per_player_cents') return `$${(Number(value) / 100).toFixed(2)}`
  if (field === 'starts_at' || field === 'ends_at') {
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return String(value)
    // Show times in the game's own time zone, like the rest of the page.
    return new Intl.DateTimeFormat('en-US', {
      dateStyle: 'medium',
      timeStyle: 'short',
      timeZone: timeZone || undefined,
    }).format(date)
  }
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

export function GameChangeReviewCard({ error, isSubmitting, onSubmit, review, status, timeZone }) {
  const [choice, setChoice] = useState('')

  if (status === 'idle') return null

  if (status === 'loading') {
    return <p className="details-change-review__status">Checking for changes to your booking…</p>
  }

  if (status === 'error') {
    return <p className="details-change-review__status" role="alert">{error}</p>
  }

  if (!review?.changes?.length && !review?.active_request) return null

  async function handleSubmit(event) {
    event.preventDefault()
    await onSubmit(choice)
  }

  return (
    <section className="details-card details-change-review" aria-labelledby="details-change-review-title">
      <h2 id="details-change-review-title">Game details changed</h2>
      <p>Review what changed since you booked. Your spot stays confirmed unless staff process a request to leave.</p>
      {review.changes?.length > 0 && (
        <ul>
          {review.changes.map((change) => (
            <li key={change.field}>
              <strong>{FIELD_LABELS[change.field] || change.field.replaceAll('_', ' ')}</strong>
              <span>{displayValue(change.field, change.before, timeZone)} → {displayValue(change.field, change.after, timeZone)}</span>
            </li>
          ))}
        </ul>
      )}
      {review.active_request ? (
        <p role="status">Your request to leave is {REQUEST_STATUS_TEXT[review.active_request.request_status] || review.active_request.request_status}. Your booking stays confirmed until staff process it.</p>
      ) : review.can_request_removal ? (
        <form onSubmit={handleSubmit}>
          <fieldset disabled={isSubmitting}>
            <legend>If these changes no longer work for you, choose how to receive eligible value when staff remove your booking:</legend>
            <label><input type="radio" name="removal-relief" value="original_payment_method" checked={choice === 'original_payment_method'} onChange={(event) => setChoice(event.target.value)} /> Refund to original payment method</label>
            <label><input type="radio" name="removal-relief" value="game_credit" checked={choice === 'game_credit'} onChange={(event) => setChoice(event.target.value)} /> Game credit</label>
            <button type="submit" disabled={!choice || isSubmitting}>{isSubmitting ? 'Sending request…' : 'Request to leave'}</button>
          </fieldset>
        </form>
      ) : null}
      {error && <p role="alert">{error}</p>}
    </section>
  )
}
