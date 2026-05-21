import { Link } from 'react-router-dom'
import {
  formatNeedLabel,
  formatStatus,
} from './needASubFormatters.js'
import { countHeldSpots } from './needASubSelectors.js'
import { NeedASubStatusChip } from './NeedASubStatusChip.jsx'

export function NeedASubRequestPanel({
  activeRequest,
  canRequest,
  canSubmitRequest,
  currentUser,
  isActing,
  isPostWaitlistFull,
  onCancelRequest,
  onRequestSpot,
  onSelectPosition,
  post,
  requestNotice,
  selectedPositionId,
  selectedPositionNeedsWaitlist,
}) {
  return (
    <section className="need-sub-manage-card need-sub-detail-card need-sub-detail-card--request">
      <div className="need-sub-action-card-header">
        <p>{activeRequest ? getRequestHeader(activeRequest) : 'Request a Spot'}</p>
        {requestNotice && (
          <NeedASubStatusChip>
            {requestNotice}
          </NeedASubStatusChip>
        )}
      </div>

      {activeRequest ? (
        <RequestStatusCard
          isActing={isActing}
          request={activeRequest}
          onCancel={onCancelRequest}
        />
      ) : (
        <select
          className="need-sub-detail-choice"
          disabled={!canRequest}
          value={selectedPositionId}
          onChange={(event) => onSelectPosition(event.target.value)}
        >
          {(post.positions || []).map((position) => (
            <option key={position.id} value={position.id}>
              {formatSpotOption(position)}
            </option>
          ))}
        </select>
      )}

      {!currentUser && (
        <div className="need-sub-detail-request-box">
          <Link to="/sign-in" state={{ from: `/need-a-sub/posts/${post.id}` }}>
            Sign In to Request
          </Link>
        </div>
      )}

      {canRequest && !activeRequest && (
        <div className="need-sub-detail-request-box">
          <button
            disabled={isActing || !canSubmitRequest}
            type="button"
            onClick={onRequestSpot}
          >
            {selectedPositionNeedsWaitlist
              ? isPostWaitlistFull
                ? 'Waitlist Full'
                : 'Join Waitlist'
              : 'Request Spot'}
          </button>
          <span>
            {selectedPositionNeedsWaitlist
              ? isPostWaitlistFull
                ? 'This post has reached the waitlist limit.'
                : 'You will be added behind current waitlisted players.'
              : 'The owner will review your request.'}
          </span>
        </div>
      )}
    </section>
  )
}

function formatPositionAvailability(position) {
  const spotsLeft = Math.max(0, Number(position.spots_needed || 0) - countHeldSpots(position))
  if (spotsLeft === 0) {
    return 'Join Waitlist'
  }
  return `${spotsLeft} ${spotsLeft === 1 ? 'Spot' : 'Spots'} Available`
}

function formatSpotOption(position) {
  return `${formatNeedLabel(position)} · ${formatPositionAvailability(position)}`
}

function getRequestHeader(request) {
  return {
    pending: 'Request Pending',
    confirmed: 'Spot Confirmed',
    sub_waitlist: 'Waitlisted',
  }[request.request_status] || formatStatus(request.request_status)
}

function RequestStatusCard({ request, isActing, onCancel }) {
  const isWaitlisted = request.request_status === 'sub_waitlist'
  const waitlistAhead = Number(request.waitlist_ahead_count || 0)
  const copy = {
    pending: 'The owner is reviewing your request.',
    confirmed: 'You are in for this spot.',
    sub_waitlist: waitlistAhead > 0
      ? `${waitlistAhead} ${waitlistAhead === 1 ? 'player' : 'players'} ahead of you.`
      : 'You are next if a review spot opens.',
  }[request.request_status] || ''

  return (
    <div className="need-sub-detail-request-status">
      <div className="need-sub-detail-request-status__copy">
        {copy && <small>{copy}</small>}
      </div>
      <button disabled={isActing} type="button" onClick={onCancel}>
        {isWaitlisted
          ? 'Leave Waitlist'
          : request.request_status === 'confirmed'
            ? 'Cancel Spot'
            : 'Cancel Request'}
      </button>
    </div>
  )
}
