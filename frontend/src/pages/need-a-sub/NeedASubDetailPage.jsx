import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { AppPageShell } from '../../components/app/index.js'
import {
  CalendarIcon,
  ClockIcon,
  MapPinIcon,
  UsersIcon,
} from '../../components/BrowseIcons.jsx'
import { useAuth } from '../../hooks/useAuth.js'
import {
  cancelNeedASubRequest,
  getNeedASubPost,
  listNeedASubPostRequests,
  listMyNeedASubRequests,
  requestNeedASubSpot,
} from './needASubApi.js'
import { MAX_WAITLIST_REQUESTS_PER_POST } from './needASubData.js'
import {
  buildPostSubtitle,
  formatDateWithYear,
  formatLocation,
  formatNeedLabel,
  formatPrice,
  formatStatus,
  formatTimeRangeOnly,
} from './needASubFormatters.js'
import { countHeldSpots } from './needASubSelectors.js'
import '../../styles/need-a-sub.css'

function HighlightedPostHeadline({ post }) {
  return (
    <>
      Need <span>{post.subs_needed}</span> {post.subs_needed === 1 ? 'Sub' : 'Subs'}
    </>
  )
}

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
  const isOwner = Boolean(appUser?.id && post?.owner_user_id === appUser.id)
  const canRequest = Boolean(
    currentUser &&
    ['active', 'filled'].includes(post?.post_status) &&
    !isOwner &&
    !activeRequest,
  )
  const selectedPosition = (post?.positions || []).find((position) => position.id === selectedPositionId)
  const selectedPositionNeedsWaitlist = selectedPosition
    ? countHeldSpots(selectedPosition) >= selectedPosition.spots_needed
    : false
  const isPostWaitlistFull = Number(post?.sub_waitlist_count || 0) >= MAX_WAITLIST_REQUESTS_PER_POST
  const canSubmitRequest = Boolean(
    canRequest &&
    selectedPosition &&
    (!selectedPositionNeedsWaitlist || !isPostWaitlistFull),
  )
  const requestNotice = notice && !isOwner
    ? notice
    : ''

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
      const postResponse = await getNeedASubPost(postId, currentUser)
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
    <AppPageShell className="need-sub-page" mainClassName="need-sub-shell need-sub-detail-shell">
        <div className="need-sub-manage-top">
          <Link className="need-sub-back-link" to="/need-a-sub">← Back</Link>
        </div>

        {error && (
          <div className="need-sub-alert need-sub-alert--error">
            {error}
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
            <div className="need-sub-detail-grid">
              <section className="need-sub-detail-hero need-sub-detail-card--summary">
                <div className="need-sub-detail-hero__copy">
                  <div className="need-sub-detail-hero__title-row">
                    <h1><HighlightedPostHeadline post={post} /></h1>
                    {post.environment_type && (
                      <span className="need-sub-detail-environment">
                        {formatStatus(post.environment_type)}
                      </span>
                    )}
                  </div>
                  <strong>{buildPostSubtitle(post)}</strong>
                  <div className="need-sub-manage-facts">
                    <Fact icon={<CalendarIcon />} text={formatDateWithYear(post.starts_at)} />
                    <Fact icon={<ClockIcon />} text={formatTimeRangeOnly(post)} />
                    <Fact icon={<MapPinIcon />} text={formatLocation(post)} />
                  </div>
                </div>

                <div className="need-sub-detail-divider" />

                <div className="need-sub-detail-summary-block">
                  <p>Post Details</p>
                  <div className="need-sub-detail-summary">
                    <DetailSummaryItem icon={<MapPinIcon />} label="Address">
                      {post.address_line_1 || 'Sign in to view exact street details'}
                    </DetailSummaryItem>
                    <DetailSummaryItem icon={<UsersIcon />} label="Neighborhood">
                      {post.neighborhood || 'Not listed'}
                    </DetailSummaryItem>
                    <DetailSummaryItem icon={<PriceIcon />} label="Price due at venue">
                      {formatPrice(post.price_due_at_venue_cents)}
                    </DetailSummaryItem>
                    {post.notes && (
                      <DetailSummaryItem className="need-sub-detail-summary-item--notes" icon={<NoteIcon />} label="Notes">
                        {post.notes}
                      </DetailSummaryItem>
                    )}
                  </div>
                </div>
              </section>

              {isOwner ? (
                <OwnerRequestPanel postId={post.id} requests={ownerRequests} />
              ) : (
                <section className="need-sub-manage-card need-sub-detail-card need-sub-detail-card--request">
                  <div className="need-sub-action-card-header">
                    <p>{activeRequest ? getRequestHeader(activeRequest) : 'Request a Spot'}</p>
                    {requestNotice && (
                      <StatusChip>
                        {requestNotice}
                      </StatusChip>
                    )}
                  </div>

                  {activeRequest ? (
                    <RequestStatusCard
                      isActing={isActing}
                      request={activeRequest}
                      onCancel={() =>
                        runAction(
                          () => cancelNeedASubRequest(currentUser, activeRequest.id),
                          activeRequest.request_status === 'sub_waitlist'
                            ? 'Left waitlist'
                            : 'Request canceled',
                        )
                      }
                    />
                  ) : (
                    <>
                      <select
                        className="need-sub-detail-choice"
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
                    </>
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
                        onClick={() =>
                          runAction(
                            () => requestNeedASubSpot(currentUser, post.id, selectedPosition.id),
                            selectedPositionNeedsWaitlist
                              ? 'Added to waitlist'
                              : 'Request sent',
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
              )}
            </div>
          </>
        )}
    </AppPageShell>
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

function StatusChip({ children }) {
  return (
    <span className="need-sub-status-chip">
      {children}
    </span>
  )
}

function DetailSummaryItem({ children, className = '', icon, label }) {
  return (
    <div className={`need-sub-detail-summary-item ${className}`.trim()}>
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
  const manageTarget = `/need-a-sub/posts/${postId}/manage`
  const reviewTarget = `${manageTarget}#requests`
  const actionTarget = hasPendingRequests ? reviewTarget : manageTarget

  return (
    <section className={`need-sub-manage-card need-sub-detail-card need-sub-detail-card--owner need-sub-owner-panel ${hasPendingRequests ? 'need-sub-owner-panel--urgent' : ''}`}>
      <div className="need-sub-action-card-header">
        <span className="need-sub-owner-panel__eyebrow">Owner actions</span>
        {hasPendingRequests && <StatusChip>Needs review</StatusChip>}
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

      <Link className="need-sub-owner-panel__primary" to={actionTarget}>
        {hasPendingRequests ? 'Review Requests' : 'Manage Post'}
      </Link>
    </section>
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

export default NeedASubDetailPage
