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
  acceptNeedASubRequest,
  cancelNeedASubPost,
  cancelNeedASubRequestByOwner,
  declineNeedASubRequest,
  getNeedASubPost,
  listNeedASubPostRequests,
  updateNeedASubPost,
} from '../lib/needASubApi.js'
import {
  CreateNeedASubForm,
  buildCreatePayload,
  getNextPosition,
  hydrateNeedASubForm,
  validateForm,
} from './NeedASubPage.jsx'
import '../styles/browse-games/BrowseGamesPage.css'
import '../styles/need-a-sub.css'

function NeedASubManagePage() {
  const { postId } = useParams()
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
  const [waitlistModalGroup, setWaitlistModalGroup] = useState(null)

  async function loadManageView() {
    setIsLoading(true)
    setError('')

    try {
      const postResponse = await getNeedASubPost(postId)
      setPost(postResponse)

      if (currentUser) {
        const requestResponse = await listNeedASubPostRequests(currentUser, postId)
        setRequests(requestResponse)
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
  }, [postId, currentUser])

  const requestGroups = useMemo(
    () =>
      (post?.positions || []).map((position, index) => {
        const positionRequests = requests.filter(
          (request) => request.sub_post_position_id === position.id,
        )
        const pending = positionRequests.filter((request) => request.request_status === 'pending')
        const confirmed = positionRequests.filter((request) => request.request_status === 'confirmed')
        const waitlisted = positionRequests.filter((request) => request.request_status === 'sub_waitlist')

        return {
          position,
          label: `Sub need ${index + 1}`,
          pending,
          confirmed,
          waitlisted,
        }
      }),
    [post?.positions, requests],
  )
  const selectedGroup = useMemo(
    () =>
      requestGroups.find((group) => group.position.id === selectedPositionId)
      || requestGroups[0]
      || null,
    [requestGroups, selectedPositionId],
  )
  const manageSummary = useMemo(() => {
    const totalNeeded = (post?.positions || []).reduce(
      (sum, position) => sum + Number(position.spots_needed || 0),
      0,
    )
    const confirmed = requestGroups.reduce((sum, group) => sum + group.confirmed.length, 0)
    const pending = requestGroups.reduce((sum, group) => sum + group.pending.length, 0)
    const waitlisted = requestGroups.reduce((sum, group) => sum + group.waitlisted.length, 0)

    return {
      confirmed,
      needed: totalNeeded,
      open: Math.max(0, totalNeeded - confirmed),
      pending,
      waitlisted,
    }
  }, [post?.positions, requestGroups])
  const canCancelPost = post && ['active', 'filled'].includes(post.post_status)
  const isOwner = post?.owner_user_id === appUser?.id
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
      setSelectedPositionId(requestGroups[0].position.id)
    }
  }, [requestGroups, selectedPositionId])

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

    const validationError = validateForm(editForm)
    if (validationError) {
      setEditError(validationError)
      return
    }

    setIsSavingEdit(true)
    try {
      const payload = buildCreatePayload(editForm, totalEditSpotsNeeded)
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
    <div className="need-sub-page">
      <BrowseAppNav />

      <main className="need-sub-shell need-sub-manage-shell">
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
        ) : !isOwner ? (
          <div className="need-sub-empty">
            <strong>You can only manage posts you created.</strong>
            <span>This post is visible from the All Posts tab.</span>
          </div>
        ) : (
          isEditing && editForm ? (
            <>
              <div className="need-sub-edit-toolbar">
                <button type="button" onClick={() => setIsEditing(false)}>
                  Cancel edit
                </button>
              </div>
              <CreateNeedASubForm
                form={editForm}
                formError={editError}
                isCreating={isSavingEdit}
                onAddPosition={addEditPosition}
                onRemovePosition={removeEditPosition}
                onSubmit={submitEdit}
                onUpdateField={updateEditField}
                onUpdateGamePlayerGroup={updateEditGamePlayerGroup}
                onUpdatePosition={updateEditPosition}
                submitLabel="Save Changes"
                totalSpotsNeeded={totalEditSpotsNeeded}
              />
            </>
          ) : (
          <>
            <section className="need-sub-manage-hero">
              <div>
                <p>Manage post</p>
                <h1>{buildManageTitle(post)}</h1>
                <strong className="need-sub-manage-subtitle">{buildManageSubtitle(post)}</strong>
                <div className="need-sub-manage-facts">
                  <Fact icon={<CalendarIcon />} text={formatDate(post.starts_at)} />
                  <Fact icon={<ClockIcon />} text={`${formatTime(post.starts_at)}-${formatTime(post.ends_at)}`} />
                  <Fact icon={<MapPinIcon />} text={`${post.location_name} · ${post.city}, ${post.state}`} />
                </div>
              </div>

              <div className="need-sub-manage-actions">
                <button type="button" onClick={beginEdit}>
                  Edit post
                </button>
                <button
                  className="need-sub-danger-action"
                  disabled={!canCancelPost}
                  type="button"
                  onClick={() =>
                    runAction(
                      () => cancelNeedASubPost(currentUser, post.id, 'Canceled by host.'),
                      'Post canceled.',
                    )
                  }
                >
                  Cancel post
                </button>
              </div>
              <div className="need-sub-manage-summary" aria-label="Post player summary">
                <SummaryStat icon={<UsersIcon />} label={`${manageSummary.confirmed} / ${manageSummary.needed} filled`} />
                <SummaryStat label={`${manageSummary.pending} pending`} tone="yellow" />
                <SummaryStat label={`${manageSummary.waitlisted} waitlisted`} />
              </div>
            </section>

            <div className="need-sub-manage-focus-grid" id="requests">
              <section className="need-sub-manage-card need-sub-subneeds-panel">
                <p>Sub needs</p>
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
      </main>
    </div>
  )
}

function SummaryStat({ icon = null, label, tone = '' }) {
  return (
    <span className={`need-sub-manage-summary__stat ${tone ? `need-sub-manage-summary__stat--${tone}` : ''}`}>
      {icon}
      {label}
    </span>
  )
}

function SubNeedSelector({ group, isSelected, onSelect }) {
  const openSpots = Math.max(0, Number(group.position.spots_needed || 0) - group.confirmed.length)

  return (
    <button
      className={`need-sub-need-option ${isSelected ? 'need-sub-need-option--selected' : ''}`}
      type="button"
      onClick={onSelect}
    >
      <span className="need-sub-need-option__icon" aria-hidden="true">
        <UsersIcon />
      </span>
      <span className="need-sub-need-option__body">
        <strong>{formatNeedLabel(group.position)}</strong>
      </span>
      <span className="need-sub-need-option__status">
        {openSpots > 0 ? `${openSpots} Open` : 'Full'}
      </span>
    </button>
  )
}

function PlayerPanel({ group, onAccept, onDecline, onRemove, onViewWaitlist }) {
  const visibleWaitlist = group.waitlisted.slice(0, 1)

  return (
    <section className="need-sub-manage-card need-sub-player-panel">
      <header className="need-sub-player-panel__header">
        <div>
          <p>Players</p>
          <strong>{formatNeedLabel(group.position)}</strong>
        </div>
      </header>

      <div className="need-sub-player-sections">
        <PlayerSection
          label="Pending"
          requests={group.pending}
          renderActions={(request) => (
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
          )}
        />
        <PlayerSection
          label="Confirmed"
          requests={group.confirmed}
          renderActions={(request) => (
            <button
              className="need-sub-secondary-action"
              type="button"
              onClick={() => onRemove(request)}
            >
              Remove
            </button>
          )}
        />
        <PlayerSection
          label="Waitlist"
          requests={visibleWaitlist}
          waitlistTotal={group.waitlisted.length}
          onViewWaitlist={onViewWaitlist}
        />
      </div>
    </section>
  )
}

function PlayerSection({
  label,
  onViewWaitlist = null,
  renderActions = null,
  requests,
  waitlistTotal = 0,
}) {
  const isWaitlist = label === 'Waitlist'

  if (!requests.length) {
    return (
      <section className="need-sub-player-section">
        <div className="need-sub-player-section__header">
          <span>{label} (0)</span>
        </div>
        <div className="need-sub-manage-empty need-sub-manage-empty--center">None yet</div>
      </section>
    )
  }

  return (
    <section className="need-sub-player-section">
      <div className="need-sub-player-section__header">
        <span>{label} ({isWaitlist ? waitlistTotal : requests.length})</span>
      </div>
      <div className="need-sub-manage-request-list">
        {requests.map((request, index) => (
          <PlayerRow
            key={request.id}
            request={request}
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

function PlayerRow({ renderActions, request, waitlistPosition = null }) {
  return (
    <div className="need-sub-manage-request">
      <span className="need-sub-manage-request__avatar" aria-hidden="true">
        {getRequesterInitials(request)}
      </span>
      <div>
        <strong>{getRequesterName(request)}</strong>
        {waitlistPosition && <span>#{waitlistPosition} in line</span>}
      </div>
      {renderActions && (
        <div className="need-sub-manage-request__actions">
          {renderActions(request)}
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

function buildManageTitle(post) {
  return `Need ${post.subs_needed} ${post.subs_needed === 1 ? 'Sub' : 'Subs'}`
}

function buildManageSubtitle(post) {
  return `${formatStatus(post.game_player_group)} ${post.format_label} · ${formatStatus(post.skill_level)}`
}

function formatNeedLabel(position) {
  const spots = Number(position.spots_needed || 0)
  const group = formatStatus(position.player_group)
  const label = formatStatus(position.position_label)

  return `${spots} ${spots === 1 ? 'Sub' : 'Subs'} · ${group} · ${label}`
}

function formatStatus(value) {
  return String(value || '')
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function formatDate(value) {
  return new Intl.DateTimeFormat('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  }).format(new Date(value))
}

function formatTime(value) {
  return new Intl.DateTimeFormat('en-US', {
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(value))
}

function getRequesterName(request) {
  return request.requester_display_name || 'Pickup Lane Player'
}

function getRequesterInitials(request) {
  return request.requester_initials || 'PL'
}

export default NeedASubManagePage
