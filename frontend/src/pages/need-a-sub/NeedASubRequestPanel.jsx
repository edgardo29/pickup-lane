import { Link } from 'react-router-dom'
import { SinglePlayerIcon } from '../../components/GameFactIcons.jsx'
import {
  formatNeedType,
  formatStatus,
} from './needASubFormatters.js'
import { countHeldSpots } from './needASubSelectors.js'
import { NeedASubStatusChip } from './NeedASubStatusChip.jsx'

export function NeedASubRequestPanel({
  activeRequest,
  canRequest,
  canSubmitRequest,
  canSelectSpot,
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
        <span className="need-sub-action-card-heading">
          <SinglePlayerIcon aria-hidden="true" />
          <span>{activeRequest ? getRequestHeader(activeRequest) : 'Request a Spot'}</span>
        </span>
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
        <div className="need-sub-detail-choice-group">
          <AvailabilityValue post={post} isPostWaitlistFull={isPostWaitlistFull} />
          <label htmlFor="need-sub-position-choice">Choose spot</label>
          <select
            className="need-sub-detail-choice"
            disabled={!canSelectSpot}
            id="need-sub-position-choice"
            value={selectedPositionId}
            onChange={(event) => onSelectPosition(event.target.value)}
          >
            {(post.positions || []).map((position) => (
              <option key={position.id} value={position.id}>
                {formatSpotOption(position, isPostWaitlistFull)}
              </option>
            ))}
          </select>
        </div>
      )}

      {!currentUser && (
        <div className="need-sub-detail-request-box">
          <Link to="/sign-in" state={{ from: `/need-a-sub/posts/${post.id}` }}>
            Sign In to Request
          </Link>
          <span>Choose a spot type, then sign in to send your request.</span>
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
                ? "This post's waitlist is full."
                : "You'll be notified if a spot opens."
              : 'The owner will review your request.'}
          </span>
        </div>
      )}
    </section>
  )
}

function AvailabilityValue({ post, isPostWaitlistFull }) {
  const spotsLeft = getPostSpotsLeft(post)
  const isFull = spotsLeft === 0

  return (
    <div className="need-sub-detail-availability">
      <span>Availability</span>
      <strong className={isFull ? 'need-sub-detail-availability__full' : ''}>
        {formatPostAvailability(post, isPostWaitlistFull)}
      </strong>
    </div>
  )
}

function formatPostAvailability(post, isPostWaitlistFull) {
  const spotsLeft = getPostSpotsLeft(post)

  if (spotsLeft > 0) {
    return `${spotsLeft} ${spotsLeft === 1 ? 'spot' : 'spots'} available`
  }

  return isPostWaitlistFull ? 'FULL · Waitlist full' : 'FULL · Waitlist open'
}

function formatPositionAvailability(position, isPostWaitlistFull) {
  const spotsLeft = getSpotsLeft(position)

  if (spotsLeft === 0) {
    return isPostWaitlistFull ? 'Waitlist full' : 'Join waitlist'
  }

  return `${spotsLeft} ${spotsLeft === 1 ? 'spot' : 'spots'} left`
}

function formatSpotOption(position, isPostWaitlistFull) {
  return `${formatNeedType(position)} · ${formatPositionAvailability(position, isPostWaitlistFull)}`
}

function getSpotsLeft(position) {
  return Math.max(0, Number(position.spots_needed || 0) - countHeldSpots(position))
}

function getPostSpotsLeft(post) {
  return (post.positions || []).reduce(
    (sum, position) => sum + getSpotsLeft(position),
    0,
  )
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
