import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import BrowseAppNav from '../components/BrowseAppNav.jsx'
import {
  CalendarIcon,
  ClockIcon,
  MapPinIcon,
  UsersIcon,
} from '../components/BrowseIcons.jsx'
import { useAuth } from '../hooks/useAuth.js'
import {
  cancelNeedASubRequest,
  getNeedASubPost,
  listNeedASubPostRequests,
  listMyNeedASubRequests,
  requestNeedASubSpot,
} from '../lib/needASubApi.js'
import {
  buildPostHeadline,
  countHeldSpots,
  formatDate,
  formatNeedLabel,
  formatStatus,
  formatTime,
  getSpotsLeft,
} from './NeedASubPage.jsx'
import '../styles/browse-games.css'
import '../styles/need-a-sub.css'

const MAX_WAITLIST_REQUESTS_PER_POST = 25

function NeedASubDetailPage() {
  const { postId } = useParams()
  const { appUser, currentUser } = useAuth()
  const [post, setPost] = useState(null)
  const [myRequests, setMyRequests] = useState([])
  const [ownerRequests, setOwnerRequests] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [isActing, setIsActing] = useState(false)
  const [selectedPositionId, setSelectedPositionId] = useState('')
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')

  const postRequests = useMemo(
    () => myRequests.filter((request) => request.sub_post_id === postId),
    [myRequests, postId],
  )
  const activeRequest = useMemo(
    () =>
      postRequests.find((request) =>
        ['pending', 'confirmed', 'sub_waitlist'].includes(request.request_status),
      ),
    [postRequests],
  )
  const isOwner = post?.owner_user_id === appUser?.id
  const canRequest = post?.post_status === 'active' && !isOwner && !activeRequest
  const selectedPosition = (post?.positions || []).find((position) => position.id === selectedPositionId)
  const selectedPositionNeedsWaitlist = selectedPosition
    ? countHeldSpots(selectedPosition) >= selectedPosition.spots_needed
    : false
  const isPostWaitlistFull = Number(post?.sub_waitlist_count || 0) >= MAX_WAITLIST_REQUESTS_PER_POST
  const canSubmitRequest = canRequest && selectedPosition && (!selectedPositionNeedsWaitlist || !isPostWaitlistFull)

  useEffect(() => {
    if (!post || selectedPositionId) {
      return
    }

    const firstPosition = post.positions?.[0]
    if (firstPosition) {
      setSelectedPositionId(firstPosition.id)
    }
  }, [post, selectedPositionId])

  async function loadDetail() {
    setIsLoading(true)
    setError('')

    try {
      const postResponse = await getNeedASubPost(postId)
      const isPostOwner = appUser?.id === postResponse.owner_user_id
      const [requestResponse, ownerRequestResponse] = await Promise.all([
        currentUser && !isPostOwner
          ? listMyNeedASubRequests(currentUser).catch(() => [])
          : Promise.resolve([]),
        currentUser && isPostOwner
          ? listNeedASubPostRequests(currentUser, postId).catch(() => [])
          : Promise.resolve([]),
      ])
      setPost(postResponse)
      setMyRequests(requestResponse)
      setOwnerRequests(ownerRequestResponse)
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Unable to load post.')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadDetail()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [postId, currentUser, appUser?.id])

  async function runAction(action, successMessage) {
    setIsActing(true)
    setNotice('')
    setError('')

    try {
      await action()
      setNotice(successMessage)
      await loadDetail()
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : 'Unable to update request.')
    } finally {
      setIsActing(false)
    }
  }

  return (
    <div className="need-sub-page">
      <BrowseAppNav />

      <main className="need-sub-shell need-sub-detail-shell">
        <div className="need-sub-manage-top">
          <Link to="/need-a-sub">Back to Need a Sub</Link>
        </div>

        {(notice || error) && (
          <div className={`need-sub-alert ${error ? 'need-sub-alert--error' : ''}`}>
            {error || notice}
          </div>
        )}

        {isLoading ? (
          <div className="need-sub-empty">Loading post...</div>
        ) : !post ? (
          <div className="need-sub-empty">
            <strong>Post not found.</strong>
            <span>Go back to Need a Sub and choose another post.</span>
          </div>
        ) : (
          <>
            <section className="need-sub-detail-hero">
              <div>
                <p>Need a Sub</p>
                <h1>{buildPostHeadline(post)}</h1>
                <div className="need-sub-manage-facts">
                  <Fact icon={<CalendarIcon />} text={formatDate(post.starts_at)} />
                  <Fact icon={<ClockIcon />} text={formatTimeRange(post)} />
                  <Fact icon={<MapPinIcon />} text={`${post.location_name} · ${post.city}, ${post.state}`} />
                </div>
              </div>
              <div className="need-sub-detail-status">
                <strong>{getSpotsLeft(post)}</strong>
                <span>{getSpotsLeft(post) === 1 ? 'Spot Left' : 'Spots Left'}</span>
              </div>
            </section>

            <div className="need-sub-detail-grid">
              <section className="need-sub-manage-card need-sub-detail-card">
                <p>Choose a Spot</p>
                <span className="need-sub-detail-card-copy">
                  Select the spot you would like to request.
                </span>

                {activeRequest ? (
                  <RequestStatusCard
                    isActing={isActing}
                    request={activeRequest}
                    onCancel={() =>
                      runAction(
                        () => cancelNeedASubRequest(currentUser, activeRequest.id),
                        activeRequest.request_status === 'sub_waitlist'
                          ? 'Left waitlist.'
                          : 'Request canceled.',
                      )
                    }
                  />
                ) : (
                  <>
                    <label className="need-sub-detail-choice">
                      <span>Spot</span>
                      <select
                        disabled={!canRequest}
                        value={selectedPositionId}
                        onChange={(event) => setSelectedPositionId(event.target.value)}
                      >
                        {(post.positions || []).map((position) => (
                          <option key={position.id} value={position.id}>
                            {formatSpotOption(position)}
                          </option>
                        ))}
                      </select>
                    </label>
                  </>
                )}

                {canRequest && !activeRequest && (
                  <div className="need-sub-detail-request-box">
                    <button
                      disabled={isActing || !canSubmitRequest}
                      type="button"
                      onClick={() =>
                        runAction(
                          () => requestNeedASubSpot(currentUser, post.id, selectedPosition.id),
                          selectedPositionNeedsWaitlist
                            ? 'Added to waitlist.'
                            : 'Request sent.',
                        )
                      }
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

              <aside className="need-sub-manage-card need-sub-detail-card">
                <p>Post Details</p>
                <div className="need-sub-detail-summary">
                  <DetailSummaryItem icon={<MapPinIcon />} label="Address">
                    {post.address_line_1}
                  </DetailSummaryItem>
                  <DetailSummaryItem icon={<UsersIcon />} label="Neighborhood">
                    {post.neighborhood || 'Not listed'}
                  </DetailSummaryItem>
                  <DetailSummaryItem icon={<PriceIcon />} label="Price due at venue">
                    {formatPrice(post.price_due_at_venue_cents)}
                  </DetailSummaryItem>
                  {post.notes && (
                    <DetailSummaryItem icon={<NoteIcon />} label="Notes">
                      {post.notes}
                    </DetailSummaryItem>
                  )}
                </div>

                {isOwner ? (
                  <OwnerRequestPanel postId={post.id} requests={ownerRequests} />
                ) : null}
              </aside>
            </div>
          </>
        )}
      </main>
    </div>
  )
}

function Fact({ icon, text }) {
  return (
    <span>
      {icon}
      {text}
    </span>
  )
}

function formatTimeRange(post) {
  return `${formatTime(post.starts_at)}-${formatTime(post.ends_at)} · ${getDurationMinutes(post)} min`
}

function getDurationMinutes(post) {
  const startsAt = new Date(post.starts_at)
  const endsAt = new Date(post.ends_at)
  return Math.max(0, Math.round((endsAt - startsAt) / 60000))
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
        <span>Your status</span>
        <strong>{formatStatus(request.request_status)}</strong>
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

function DetailSummaryItem({ icon, label, children }) {
  return (
    <div className="need-sub-detail-summary-item">
      <span aria-hidden="true">{icon}</span>
      <div>
        <small>{label}</small>
        <strong>{children}</strong>
      </div>
    </div>
  )
}

function OwnerRequestPanel({ postId, requests }) {
  const pendingRequests = requests.filter((request) => request.request_status === 'pending')
  const confirmedRequests = requests.filter((request) => request.request_status === 'confirmed')
  const waitlistedRequests = requests.filter((request) => request.request_status === 'sub_waitlist')
  const hasPendingRequests = pendingRequests.length > 0
  const manageTarget = hasPendingRequests
    ? `/need-a-sub/posts/${postId}/manage#requests`
    : `/need-a-sub/posts/${postId}/manage`

  return (
    <div className={`need-sub-owner-panel ${hasPendingRequests ? 'need-sub-owner-panel--urgent' : ''}`}>
      <span className="need-sub-owner-panel__eyebrow">Owner actions</span>

      <div className="need-sub-owner-panel__headline">
        {hasPendingRequests ? (
          <>
            <strong>
              {pendingRequests.length} {pendingRequests.length === 1 ? 'request' : 'requests'} need review
            </strong>
            <small>Accept players or decline them from the manage screen.</small>
          </>
        ) : confirmedRequests.length > 0 ? (
          <>
            <strong>{confirmedRequests.length} {confirmedRequests.length === 1 ? 'player is' : 'players are'} confirmed</strong>
            <small>Manage confirmed players or cancel the post if plans change.</small>
          </>
        ) : waitlistedRequests.length > 0 ? (
          <>
            <strong>{waitlistedRequests.length} {waitlistedRequests.length === 1 ? 'player is' : 'players are'} waitlisted</strong>
            <small>Waitlisted players move up when a review spot opens.</small>
          </>
        ) : (
          <>
            <strong>No requests yet</strong>
            <small>Player requests will appear here when they come in.</small>
          </>
        )}
      </div>

      <div className="need-sub-owner-panel__stats" aria-label="Request summary">
        <span>
          <strong>{pendingRequests.length}</strong>
          <small>pending</small>
        </span>
        <span>
          <strong>{confirmedRequests.length}</strong>
          <small>confirmed</small>
        </span>
        <span>
          <strong>{waitlistedRequests.length}</strong>
          <small>waitlisted</small>
        </span>
      </div>

      <Link className="need-sub-owner-panel__primary" to={manageTarget}>
        {hasPendingRequests ? 'Review Requests' : 'Manage Post'}
      </Link>
    </div>
  )
}

function PriceIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 7.5v9" />
      <path d="M9.3 9.3c.7-1 2-1.3 3.3-1 1 .2 1.8.8 1.8 1.8 0 1.2-1 1.7-2.5 2-1.6.3-2.7.8-2.7 2 0 1 .9 1.7 2 1.9 1.4.3 2.8-.1 3.5-1.2" />
    </svg>
  )
}

function NoteIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M6 4.5h9l3 3v12H6Z" />
      <path d="M15 4.5v3h3" />
      <path d="M9 11h6" />
      <path d="M9 15h5" />
    </svg>
  )
}

function formatPrice(cents) {
  const amount = Number(cents || 0) / 100
  if (amount <= 0) {
    return 'Free'
  }
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(amount)
}

export default NeedASubDetailPage
