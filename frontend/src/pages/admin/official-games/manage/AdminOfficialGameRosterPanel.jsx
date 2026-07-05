import { useEffect, useRef, useState } from 'react'
import {
  ClipboardListIcon,
  TrashIcon,
  UserIcon,
  UsersIcon,
} from '../../../../components/BrowseIcons.jsx'
import AdminOfficialGameSimpleConfirmModal from './AdminOfficialGameSimpleConfirmModal.jsx'

const removableStatuses = new Set(['confirmed', 'pending_payment'])
const activeRosterStatuses = new Set(['confirmed', 'pending_payment'])
const removedRosterStatuses = new Set(['cancelled', 'late_cancelled', 'removed', 'refunded'])
const USER_SEARCH_MIN_LENGTH = 3

const eligibilityReasonLabels = {
  already_on_roster: 'Already on roster',
  current_host: 'Current host',
  game_full: 'Game is full',
  game_not_addable: 'Game cannot add players',
  game_started: 'Game already started',
  inactive_user: 'Inactive user',
}

const participantTypeLabels = {
  admin_added: 'Admin added',
  guest: 'Guest',
  host: 'Host',
  registered_user: 'Registered user',
}

const participantStatusLabels = {
  cancelled: 'Cancelled',
  confirmed: 'Confirmed',
  late_cancelled: 'Late cancelled',
  pending_payment: 'Pending payment',
  refunded: 'Refunded',
  removed: 'Removed',
  waitlisted: 'Waitlisted',
}

function getRemovalState(participant, hostUserId, canPreviewRemovals) {
  if (!removableStatuses.has(participant.participant_status)) {
    return {
      action: 'disabled',
      title: 'This roster row uses a different removal flow',
    }
  }

  if (
    participant.participant_type === 'host'
    || (participant.user_id && participant.user_id === hostUserId)
  ) {
    return {
      action: 'disabled',
      title: 'Remove host designation first',
    }
  }

  if (
    participant.participant_status === 'pending_payment'
    || participant.participant_type === 'admin_added'
  ) {
    return {
      action: 'remove',
      title: 'Remove player',
    }
  }

  return {
    action: canPreviewRemovals ? 'preview' : 'disabled',
    title: canPreviewRemovals
      ? 'Preview removal impact'
      : 'Money read permission is required to preview removal impact',
  }
}

function getEligibilityLabel(reason) {
  return eligibilityReasonLabels[reason] || 'Cannot add'
}

function formatRosterValue(value) {
  const normalizedValue = String(value || '')
  return participantTypeLabels[normalizedValue]
    || participantStatusLabels[normalizedValue]
    || normalizedValue
      .replaceAll('_', ' ')
      .replace(/^\w/, (letter) => letter.toUpperCase())
}

function getActiveRosterMetaLabel(participant) {
  const labels = []

  if (participant.participant_type !== 'registered_user') {
    labels.push(formatRosterValue(participant.participant_type))
  }

  if (participant.participant_status !== 'confirmed') {
    labels.push(formatRosterValue(participant.participant_status))
  }

  return labels.join(' · ')
}

function getRemovedRosterMetaLabel(participant) {
  const labels = []

  if (participant.participant_type !== 'registered_user') {
    labels.push(formatRosterValue(participant.participant_type))
  }
  labels.push(formatRosterValue(participant.participant_status))

  return labels.join(' · ')
}

function formatRosterDate(value) {
  if (!value) {
    return '—'
  }

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return '—'
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
  }).format(date)
}

function getParticipantEmail(participant) {
  return participant.user_email || participant.guest_email || ''
}

function getHistoryDate(participant) {
  return participant.cancelled_at || participant.updated_at || participant.joined_at
}

function getHistoryLabel(participant) {
  if (
    participant.participant_status === 'removed'
    || participant.cancellation_type === 'admin_cancelled'
  ) {
    return 'Removed'
  }

  if (
    participant.participant_status === 'late_cancelled'
    || participant.cancellation_type === 'late'
  ) {
    return 'Late drop'
  }

  if (
    participant.participant_status === 'cancelled'
    || participant.cancellation_type === 'on_time'
  ) {
    return 'Dropped'
  }

  if (participant.participant_status === 'refunded') {
    return 'Refunded'
  }

  return getRemovedRosterMetaLabel(participant)
}

function AdminOfficialGameRosterPanel({
  canAddPlayer,
  canManageRoster,
  canPreviewRemovals,
  game,
  isSaving,
  onAddPlayer,
  onRemovePlayer,
  onPreviewRemoval,
  onSearchUsers,
  participants,
}) {
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [searchState, setSearchState] = useState('idle')
  const [searchError, setSearchError] = useState('')
  const [selectedUser, setSelectedUser] = useState(null)
  const [pendingAddUser, setPendingAddUser] = useState(null)
  const [pendingRemoveParticipant, setPendingRemoveParticipant] = useState(null)
  const [activeRosterView, setActiveRosterView] = useState('active')
  const searchRequestIdRef = useRef(0)
  const activeParticipants = participants.filter((participant) =>
    activeRosterStatuses.has(participant.participant_status),
  )
  const removedParticipants = participants.filter((participant) =>
    removedRosterStatuses.has(participant.participant_status),
  )
  const rosterCapacityLabel = `${activeParticipants.length} / ${game.total_spots} players`

  useEffect(() => {
    if (!canAddPlayer || !onSearchUsers) {
      return undefined
    }

    const query = searchQuery.trim()
    if (selectedUser && query === selectedUser.display_name) {
      setSearchResults([])
      setSearchState('idle')
      setSearchError('')
      return undefined
    }

    if (query.length < USER_SEARCH_MIN_LENGTH) {
      setSearchResults([])
      setSearchState('idle')
      setSearchError('')
      return undefined
    }

    const requestId = searchRequestIdRef.current + 1
    const abortController = new AbortController()
    searchRequestIdRef.current = requestId
    setSearchState('loading')
    setSearchError('')

    const timeoutId = window.setTimeout(async () => {
      try {
        const response = await onSearchUsers({
          query,
          signal: abortController.signal,
        })
        if (searchRequestIdRef.current !== requestId) {
          return
        }

        setSearchResults(response?.results ?? [])
        setSearchState('ready')
      } catch (error) {
        if (
          abortController.signal.aborted
          || error?.name === 'AbortError'
          || searchRequestIdRef.current !== requestId
        ) {
          return
        }

        setSearchResults([])
        setSearchError(error.message || 'User search failed.')
        setSearchState('error')
      }
    }, 300)

    return () => {
      window.clearTimeout(timeoutId)
      abortController.abort()
    }
  }, [canAddPlayer, onSearchUsers, searchQuery, selectedUser])

  function handleSearchQueryChange(event) {
    setSearchQuery(event.target.value)
    setSelectedUser(null)
  }

  function handleSelectUser(user) {
    if (!user.eligibility?.can_add) {
      return
    }

    setSelectedUser(user)
    setSearchQuery(user.display_name)
    setSearchResults([])
    setSearchState('idle')
    setSearchError('')
  }

  function handleAddPlayer(event) {
    event.preventDefault()
    if (!selectedUser?.eligibility?.can_add) {
      return
    }

    setPendingAddUser(selectedUser)
  }

  async function handleConfirmAddPlayer() {
    if (!pendingAddUser?.eligibility?.can_add) {
      return
    }

    const didAdd = await onAddPlayer({ userId: pendingAddUser.user_id, reason: '' })
    if (didAdd) {
      setPendingAddUser(null)
      setSelectedUser(null)
      setSearchQuery('')
      setSearchResults([])
      setSearchState('idle')
      setSearchError('')
    }
  }

  async function handleConfirmRemovePlayer() {
    if (!pendingRemoveParticipant) {
      return
    }

    const didRemove = await onRemovePlayer({
      participant: pendingRemoveParticipant,
      reason: '',
    })
    if (didRemove) {
      setPendingRemoveParticipant(null)
    }
  }

  const hasSearchQuery = searchQuery.trim().length >= USER_SEARCH_MIN_LENGTH
  const shouldShowSearchStatus = hasSearchQuery && (
    searchState === 'loading'
    || searchState === 'error'
    || (searchState === 'ready' && searchResults.length === 0)
  )

  return (
    <>
      <section
        className="admin-official-panel admin-official-roster"
        aria-label="Official game roster"
      >
        <div className="admin-official-panel__heading admin-official-panel__heading--split">
          <div className="admin-official-panel-title-block">
            <div className="admin-official-panel-title">
              <UsersIcon />
              <h2>Roster</h2>
            </div>
          </div>
          <p className="admin-official-roster-count">{rosterCapacityLabel}</p>
        </div>

        <div
          className="admin-official-inner-tabs"
          aria-label="Roster views"
          role="tablist"
        >
          <button
            aria-selected={activeRosterView === 'active'}
            className={activeRosterView === 'active' ? 'is-active' : ''}
            role="tab"
            type="button"
            onClick={() => setActiveRosterView('active')}
          >
            Active ({activeParticipants.length})
          </button>
          <button
            aria-selected={activeRosterView === 'history'}
            className={activeRosterView === 'history' ? 'is-active' : ''}
            role="tab"
            type="button"
            onClick={() => setActiveRosterView('history')}
          >
            History ({removedParticipants.length})
          </button>
        </div>

        {canAddPlayer && activeRosterView === 'active' && (
          <form
            className="admin-official-compact-form admin-official-compact-form--roster"
            onSubmit={handleAddPlayer}
          >
            <label className="admin-official-field">
              <span>Add player</span>
              <div className="admin-official-user-search">
                <input
                  autoComplete="off"
                  placeholder="Search name or email"
                  type="search"
                  value={searchQuery}
                  onChange={handleSearchQueryChange}
                />
                {shouldShowSearchStatus && (
                  <div className="admin-official-user-search__results admin-official-user-search__results--status">
                    <p
                      className={[
                        'admin-official-user-search__status',
                        searchState === 'error'
                          ? 'admin-official-user-search__status--error'
                          : '',
                      ].filter(Boolean).join(' ')}
                    >
                      {searchState === 'loading'
                        ? 'Searching...'
                        : searchState === 'error'
                          ? searchError
                          : 'No users found'}
                    </p>
                  </div>
                )}
                {searchResults.length > 0 && (
                  <div className="admin-official-user-search__results">
                    {searchResults.map((user) => {
                      const canSelect = Boolean(user.eligibility?.can_add)
                      return (
                        <button
                          key={user.user_id}
                          className={selectedUser?.user_id === user.user_id ? 'is-selected' : ''}
                          disabled={!canSelect}
                          type="button"
                          onClick={() => handleSelectUser(user)}
                        >
                          <span>
                            <strong>{user.display_name}</strong>
                            {user.email && <small>{user.email}</small>}
                          </span>
                          <em>
                            {canSelect
                              ? formatRosterValue(user.status)
                              : getEligibilityLabel(user.eligibility?.reason)}
                          </em>
                        </button>
                      )
                    })}
                  </div>
                )}
              </div>
            </label>
            <button
              className="admin-official-button admin-official-button--primary"
              disabled={isSaving || !selectedUser?.eligibility?.can_add}
              type="submit"
            >
              <span>Add</span>
            </button>
          </form>
        )}

        {activeRosterView === 'active' && (
          <div className="admin-official-roster-list" role="table" aria-label="Active roster">
            <div
              className="admin-official-roster-table-header admin-official-roster-table-header--active"
              role="row"
            >
              <span role="columnheader">Player</span>
              <span role="columnheader">Added</span>
              {canManageRoster && <span role="columnheader">Impact</span>}
            </div>

          {activeParticipants.length === 0 && (
            <p className="admin-official-empty">No active roster players.</p>
          )}

          {activeParticipants.map((participant) => {
            const removalState = getRemovalState(
              participant,
              game.host_user_id,
              canPreviewRemovals,
            )
            const isPreview = removalState.action === 'preview'
            const isRemove = removalState.action === 'remove'
            const metaLabel = getActiveRosterMetaLabel(participant)
            const email = getParticipantEmail(participant)

            return (
              <div
                className="admin-official-roster-row admin-official-roster-row--active"
                key={participant.id}
                role="row"
              >
                <div className="admin-official-roster-player" role="cell">
                  <UserIcon />
                  <span>
                    <strong>{participant.display_name_snapshot}</strong>
                    {email && <small>{email}</small>}
                  </span>
                </div>
                <div className="admin-official-roster-added" role="cell">
                  <strong>{formatRosterDate(participant.joined_at)}</strong>
                  {metaLabel && <small>{metaLabel}</small>}
                </div>
                {canManageRoster && (
                  <div className="admin-official-roster-actions" role="cell">
                  <button
                    aria-label={
                      isPreview
                        ? `Preview removal impact for ${participant.display_name_snapshot}`
                        : `Remove ${participant.display_name_snapshot}`
                    }
                    className={[
                      'admin-official-icon-button',
                      isPreview ? 'admin-official-icon-button--preview' : '',
                      isRemove ? 'admin-official-icon-button--danger' : '',
                    ].filter(Boolean).join(' ')}
                    disabled={isSaving || (!isPreview && !isRemove)}
                    title={removalState.title}
                    type="button"
                    onClick={() => {
                      if (isPreview) {
                        onPreviewRemoval(participant)
                      } else if (isRemove) {
                        setPendingRemoveParticipant(participant)
                      }
                    }}
                  >
                    {isPreview ? <ClipboardListIcon /> : <TrashIcon />}
                  </button>
                  </div>
                )}
              </div>
            )
          })}
          </div>
        )}

        {activeRosterView === 'history' && (
          <div
            className="admin-official-roster-list admin-official-roster-list--history"
            role="table"
            aria-label="Roster history"
          >
            <div
              className="admin-official-roster-table-header admin-official-roster-table-header--history"
              role="row"
            >
              <span role="columnheader">Player</span>
              <span role="columnheader">Event</span>
              <span role="columnheader">Date</span>
            </div>

            {removedParticipants.length === 0 && (
              <p className="admin-official-empty">No roster history yet.</p>
            )}

            {removedParticipants.map((participant) => {
              const email = getParticipantEmail(participant)

              return (
                <div
                  className="admin-official-roster-row admin-official-roster-row--history"
                  key={participant.id}
                  role="row"
                >
                  <div className="admin-official-roster-player" role="cell">
                      <UserIcon />
                      <span>
                        <strong>{participant.display_name_snapshot}</strong>
                        {email && <small>{email}</small>}
                      </span>
                    </div>
                  <div className="admin-official-roster-event" role="cell">
                    {getHistoryLabel(participant)}
                  </div>
                  <div className="admin-official-roster-added" role="cell">
                    <strong>{formatRosterDate(getHistoryDate(participant))}</strong>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </section>

      {pendingAddUser && (
        <AdminOfficialGameSimpleConfirmModal
          confirmLabel="Add player"
          isSaving={isSaving}
          title={`Add ${pendingAddUser.display_name}?`}
          onClose={() => setPendingAddUser(null)}
          onConfirm={handleConfirmAddPlayer}
        />
      )}

      {pendingRemoveParticipant && (
        <AdminOfficialGameSimpleConfirmModal
          confirmLabel="Remove player"
          isSaving={isSaving}
          title={`Remove ${pendingRemoveParticipant.display_name_snapshot}?`}
          variant="danger"
          onClose={() => setPendingRemoveParticipant(null)}
          onConfirm={handleConfirmRemovePlayer}
        />
      )}
    </>
  )
}

export default AdminOfficialGameRosterPanel
