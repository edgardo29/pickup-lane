import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { AppPageShell } from '../../components/app/index.js'
import {
  CalendarIcon,
  ClockIcon,
  MapPinIcon,
  PencilIcon,
  TrashIcon,
  UserIcon,
  UsersIcon,
} from '../../components/BrowseIcons.jsx'
import { useAuth } from '../../hooks/useAuth.js'
import {
  acceptNeedASubRequest,
  cancelNeedASubPost,
  cancelNeedASubRequestByOwner,
  declineNeedASubRequest,
  getNeedASubPost,
  listNeedASubPostRequests,
  updateNeedASubPost,
} from './needASubApi.js'
import NeedASubForm from './NeedASubForm.jsx'
import { getDefaultPositions, getNextPosition } from './needASubData.js'
import { buildNeedASubPayload, hydrateNeedASubForm } from './needASubPayloads.js'
import { buildRequestGroups } from './needASubSelectors.js'
import { validateNeedASubForm } from './needASubValidation.js'
import {
  buildPostSubtitle,
  formatDateWithYear,
  formatNeedLabel,
  formatStatus,
  formatTimeRangeOnly,
  getRequesterInitials,
  getRequesterName,
} from './needASubFormatters.js'
import '../../styles/need-a-sub.css'

function HighlightedPostHeadline({ post }) {
  return (
    <>
      Need <span>{post.subs_needed}</span> {post.subs_needed === 1 ? 'Sub' : 'Subs'}
    </>
  )
}

function NeedASubManagePage() {
  const { postId } = useParams()
  const navigate = useNavigate()
  const { appUser, currentUser } = useAuth()
  const [post, setPost] = useState(null)
  const [requests, setRequests] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [isEditing, setIsEditing] = useState(false)
  const [isSavingEdit, setIsSavingEdit] = useState(false)
  const [editForm, setEditForm] = useState(null)
  const [editError, setEditError] = useState('')
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const [selectedPositionId, setSelectedPositionId] = useState('')
  const [activeRequestStatus, setActiveRequestStatus] = useState('pending')
  const [waitlistModalGroup, setWaitlistModalGroup] = useState(null)

  async function loadManageView() {
    if (!currentUser) {
      setIsLoading(false)
      setError('Sign in to manage this post.')
      return
    }

    setIsLoading(true)
    setError('')

    try {
      const postResponse = await getNeedASubPost(postId, currentUser)
      setPost(postResponse)

      const isPostOwner = appUser?.id === postResponse.owner_user_id
      if (isPostOwner) {
        const requestResponse = await listNeedASubPostRequests(currentUser, postId)
        setRequests(requestResponse)
      } else {
        setRequests([])
      }
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Unable to load post.')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadManageView()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [postId, currentUser, appUser?.id])

  const requestGroups = useMemo(
    () =>
      buildRequestGroups(post, requests),
    [post?.positions, requests],
  )
  const defaultRequestGroup = useMemo(
    () => requestGroups.find((group) => group.pending.length > 0) || requestGroups[0] || null,
    [requestGroups],
  )
  const selectedGroup = useMemo(
    () =>
      requestGroups.find((group) => group.position.id === selectedPositionId)
      || defaultRequestGroup
      || null,
    [defaultRequestGroup, requestGroups, selectedPositionId],
  )
  const canCancelPost = post && ['active', 'filled'].includes(post.post_status)
  const isOwner = Boolean(appUser?.id && post?.owner_user_id === appUser.id)
  const totalEditSpotsNeeded = useMemo(
    () => (editForm?.positions || []).reduce((sum, position) => sum + Number(position.spots_needed || 0), 0),
    [editForm?.positions],
  )

  useEffect(() => {
    if (!requestGroups.length) {
      setSelectedPositionId('')
      return
    }

    if (!requestGroups.some((group) => group.position.id === selectedPositionId)) {
      setSelectedPositionId(defaultRequestGroup?.position.id || requestGroups[0].position.id)
    }
  }, [defaultRequestGroup, requestGroups, selectedPositionId])

  async function runAction(action, successMessage) {
    try {
      await action()
      setNotice(successMessage)
      setError('')
      await loadManageView()
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : 'Unable to update post.')
    }
  }

  async function cancelPost() {
    try {
      await cancelNeedASubPost(currentUser, post.id, 'Canceled by host.')
      navigate('/need-a-sub', {
        replace: true,
        state: { needASubNotice: 'Post canceled.' },
      })
    } catch (cancelError) {
      setError(cancelError instanceof Error ? cancelError.message : 'Unable to cancel post.')
      setNotice('')
    }
  }

  function beginEdit() {
    setEditForm(hydrateNeedASubForm(post))
    setEditError('')
    setNotice('')
    setError('')
    setIsEditing(true)
  }

  function updateEditField(field, value) {
    setEditError('')
    setEditForm((currentForm) => ({ ...currentForm, [field]: value }))
  }

  function updateEditGamePlayerGroup(value) {
    setEditError('')
    setEditForm((currentForm) => ({
      ...currentForm,
      gamePlayerGroup: value,
      positions: getDefaultPositions(value),
    }))
  }

  function updateEditPosition(index, field, value) {
    setEditError('')
    setEditForm((currentForm) => ({
      ...currentForm,
      positions: currentForm.positions.map((position, currentIndex) =>
        currentIndex === index
          ? { ...position, [field]: field === 'spots_needed' ? Number(value) : value }
          : position,
      ),
    }))
  }

  function addEditPosition() {
    setEditForm((currentForm) => ({
      ...currentForm,
      positions: [
        ...currentForm.positions,
        {
          ...getNextPosition(currentForm.positions, currentForm.gamePlayerGroup),
          spots_needed: 1,
          sort_order: currentForm.positions.length,
        },
      ],
    }))
  }

  function removeEditPosition(index) {
    setEditForm((currentForm) => ({
      ...currentForm,
      positions: currentForm.positions
        .filter((_, currentIndex) => currentIndex !== index)
        .map((position, sortOrder) => ({ ...position, sort_order: sortOrder })),
    }))
  }

  async function submitEdit(event) {
    event.preventDefault()

    const validationError = validateNeedASubForm(editForm)
    if (validationError) {
      setEditError(validationError)
      return
    }

    setIsSavingEdit(true)
    try {
      const payload = buildNeedASubPayload(editForm, totalEditSpotsNeeded)
      const updatedPost = await updateNeedASubPost(currentUser, post.id, payload)
      setPost(updatedPost)
      setNotice('Post updated.')
      setError('')
      setEditError('')
      setIsEditing(false)
      await loadManageView()
    } catch (editSubmitError) {
      setEditError(editSubmitError instanceof Error ? editSubmitError.message : 'Unable to update post.')
    } finally {
      setIsSavingEdit(false)
    }
  }

  return (
    <AppPageShell className="need-sub-page" mainClassName="need-sub-shell need-sub-manage-shell">
        <div className="need-sub-manage-top">
          {isEditing ? (
            <button className="need-sub-back-link" type="button" onClick={() => setIsEditing(false)}>
              ← Back
            </button>
          ) : (
            <Link className="need-sub-back-link" to={`/need-a-sub/posts/${postId}`}>← Back</Link>
          )}
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
        ) : !isOwner ? (
          <div className="need-sub-empty">
            <strong>You can only manage posts you created.</strong>
            <span>This post is visible from the All Posts tab.</span>
          </div>
        ) : (
          isEditing && editForm ? (
            <NeedASubForm
              form={editForm}
              formError={editError}
              isDateLocked
              isSaving={isSavingEdit}
              onAddPosition={addEditPosition}
              onCancel={() => setIsEditing(false)}
              onRemovePosition={removeEditPosition}
              onSubmit={submitEdit}
              onUpdateField={updateEditField}
              onUpdateGamePlayerGroup={updateEditGamePlayerGroup}
              onUpdatePosition={updateEditPosition}
              submitLabel="Save"
              title="Edit Post"
              totalSpotsNeeded={totalEditSpotsNeeded}
            />
          ) : (
          <>
            <section className="need-sub-manage-hero">
              <div className="need-sub-manage-hero__summary">
                <span className="need-sub-manage-hero__icon" aria-hidden="true">
                  <UsersIcon />
                </span>
                <div className="need-sub-manage-hero__copy">
                  <div className="need-sub-detail-hero__title-row">
                    <h1><HighlightedPostHeadline post={post} /></h1>
                    {post.environment_type && (
                      <span className="need-sub-detail-environment">
                        {formatStatus(post.environment_type)}
                      </span>
                    )}
                  </div>
                  <strong className="need-sub-manage-subtitle">{buildPostSubtitle(post)}</strong>
                  <div className="need-sub-manage-facts">
                    <Fact icon={<CalendarIcon />} text={formatDateWithYear(post.starts_at)} />
                    <Fact icon={<ClockIcon />} text={formatTimeRangeOnly(post)} />
                    <Fact icon={<MapPinIcon />} text={`${post.location_name} · ${post.city}, ${post.state}`} />
                  </div>
                </div>
              </div>

              <div className="need-sub-manage-actions">
                <button type="button" onClick={beginEdit}>
                  <PencilIcon />
                  Edit
                </button>
                <button
                  className="need-sub-danger-action"
                  disabled={!canCancelPost}
                  type="button"
                  onClick={cancelPost}
                >
                  <TrashIcon />
                  Cancel
                </button>
              </div>
            </section>

            <div className="need-sub-manage-focus-grid" id="requests">
              <section className="need-sub-manage-card need-sub-subneeds-panel">
                <h2>Open spots</h2>
                <div className="need-sub-need-select-list">
                  {requestGroups.map((group) => (
                    <SubNeedSelector
                      group={group}
                      isSelected={selectedGroup?.position.id === group.position.id}
                      key={group.position.id}
                      onSelect={() => setSelectedPositionId(group.position.id)}
                    />
                  ))}
                </div>
              </section>

              {selectedGroup && (
                <PlayerPanel
                  activeStatus={activeRequestStatus}
                  group={selectedGroup}
                  onAccept={(request) =>
                    runAction(
                      () => acceptNeedASubRequest(currentUser, request.id),
                      'Player confirmed.',
                    )
                  }
                  onDecline={(request) =>
                    runAction(
                      () => declineNeedASubRequest(currentUser, request.id),
                      'Request declined.',
                    )
                  }
                  onRemove={(request) =>
                    runAction(
                      () => cancelNeedASubRequestByOwner(currentUser, request.id),
                      'Player removed.',
                    )
                  }
                  onStatusChange={setActiveRequestStatus}
                  onViewWaitlist={() => setWaitlistModalGroup(selectedGroup)}
                />
              )}
            </div>

            {waitlistModalGroup && (
              <WaitlistModal
                group={waitlistModalGroup}
                onClose={() => setWaitlistModalGroup(null)}
              />
            )}
          </>
          )
        )}
    </AppPageShell>
  )
}

function SubNeedSelector({ group, isSelected, onSelect }) {
  const openSpots = Math.max(0, Number(group.position.spots_needed || 0) - group.confirmed.length)
  const label = formatNeedLabel(group.position).replace(/^\d+\s+Subs?\s+·\s+/, '')

  return (
    <button
      className={`need-sub-need-option ${isSelected ? 'need-sub-need-option--selected' : ''}`}
      type="button"
      onClick={onSelect}
    >
      <span className="need-sub-need-option__icon" aria-hidden="true">
        <UserIcon />
      </span>
      <span className="need-sub-need-option__body">
        <strong>{label}</strong>
        <small>{openSpots > 0 ? `${openSpots} open` : 'Full'}</small>
      </span>
    </button>
  )
}

function PlayerPanel({
  activeStatus,
  group,
  onAccept,
  onDecline,
  onRemove,
  onStatusChange,
  onViewWaitlist,
}) {
  const selectedLabel = formatNeedLabel(group.position).replace(/^\d+\s+Subs?\s+·\s+/, '')
  const statusTabs = [
    { id: 'pending', label: 'Pending', count: group.pending.length },
    { id: 'confirmed', label: 'Confirmed', count: group.confirmed.length },
    { id: 'waitlist', label: 'Waitlist', count: group.waitlisted.length },
  ]
  const activeRequests = {
    pending: group.pending,
    confirmed: group.confirmed,
    waitlist: group.waitlisted,
  }[activeStatus] || []

  return (
    <section className="need-sub-manage-card need-sub-player-panel">
      <header className="need-sub-player-panel__header">
        <div>
          <h2>Requests</h2>
          <strong>{selectedLabel}</strong>
        </div>
      </header>

      <div className="need-sub-request-tabs" role="tablist" aria-label="Request status">
        {statusTabs.map((tab) => (
          <button
            aria-selected={activeStatus === tab.id}
            className={activeStatus === tab.id ? 'need-sub-request-tabs__tab--active' : ''}
            key={tab.id}
            role="tab"
            type="button"
            onClick={() => onStatusChange(tab.id)}
          >
            <span>{tab.label}</span>
            <strong>{tab.count}</strong>
          </button>
        ))}
      </div>

      <PlayerSection
        onViewWaitlist={onViewWaitlist}
        requests={activeRequests}
        status={activeStatus}
        waitlistTotal={group.waitlisted.length}
        renderActions={(request) => {
          if (activeStatus === 'pending') {
            return (
              <>
                <button type="button" onClick={() => onAccept(request)}>
                  Accept
                </button>
                <button
                  className="need-sub-secondary-action"
                  type="button"
                  onClick={() => onDecline(request)}
                >
                  Decline
                </button>
              </>
            )
          }

          if (activeStatus === 'confirmed') {
            return (
              <button
                className="need-sub-secondary-action"
                type="button"
                onClick={() => onRemove(request)}
              >
                Remove
              </button>
            )
          }

          return null
        }}
      />
    </section>
  )
}

function PlayerSection({
  onViewWaitlist = null,
  renderActions = null,
  requests,
  status,
  waitlistTotal = 0,
}) {
  const isWaitlist = status === 'waitlist'
  const emptyText = {
    pending: 'No pending requests',
    confirmed: 'No confirmed players',
    waitlist: 'No waitlisted players',
  }[status] || 'No requests'

  if (!requests.length) {
    return (
      <section className="need-sub-player-section need-sub-player-section--empty">
        <div className="need-sub-manage-empty need-sub-manage-empty--center">
          {emptyText}
        </div>
      </section>
    )
  }

  return (
    <section className="need-sub-player-section">
      <div className="need-sub-manage-request-list">
        {requests.map((request, index) => (
          <PlayerRow
            key={request.id}
            request={request}
            status={status}
            waitlistPosition={isWaitlist ? index + 1 : null}
            renderActions={renderActions}
          />
        ))}
      </div>
      {isWaitlist && waitlistTotal > requests.length && (
        <button className="need-sub-waitlist-link" type="button" onClick={onViewWaitlist}>
          View all {waitlistTotal} waitlisted
        </button>
      )}
    </section>
  )
}

function PlayerRow({ renderActions, request, status, waitlistPosition = null }) {
  const detailText = status === 'waitlist' && waitlistPosition
    ? `#${waitlistPosition} on waitlist`
    : ''
  const actions = renderActions?.(request)

  return (
    <div className={`need-sub-manage-request ${actions ? '' : 'need-sub-manage-request--static'}`}>
      <span className="need-sub-manage-request__avatar" aria-hidden="true">
        {getRequesterInitials(request)}
      </span>
      <div>
        <strong>{getRequesterName(request)}</strong>
        {detailText && <span>{detailText}</span>}
      </div>
      {actions && (
        <div className="need-sub-manage-request__actions">
          {actions}
        </div>
      )}
    </div>
  )
}
function WaitlistModal({ group, onClose }) {
  return (
    <div className="need-sub-modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        aria-modal="true"
        className="need-sub-waitlist-modal"
        role="dialog"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header>
          <div>
            <p>Waitlist</p>
            <h2>{formatNeedLabel(group.position)}</h2>
            <span>{group.waitlisted.length} waitlisted</span>
          </div>
          <button type="button" onClick={onClose}>
            Close
          </button>
        </header>
        <div className="need-sub-waitlist-modal__list">
          {group.waitlisted.map((request, index) => (
            <div className="need-sub-waitlist-modal__row" key={request.id}>
              <span>#{index + 1}</span>
              <span className="need-sub-manage-request__avatar" aria-hidden="true">
                {getRequesterInitials(request)}
              </span>
              <strong>{getRequesterName(request)}</strong>
            </div>
          ))}
        </div>
      </section>
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

export default NeedASubManagePage
