import { useMemo, useState } from 'react'
import {
  ClipboardListIcon,
  TrashIcon,
  UserIcon,
} from '../../../../components/BrowseIcons.jsx'
import { getAdminUserLabel } from '../shared/adminOfficialGameForm.js'

const removableStatuses = new Set(['confirmed', 'pending_payment'])

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

function getAvailableUsers(users, participants, hostUserId) {
  const activeUserIds = new Set(
    participants
      .filter((participant) => removableStatuses.has(participant.participant_status))
      .map((participant) => participant.user_id)
      .filter(Boolean),
  )

  if (hostUserId) {
    activeUserIds.add(hostUserId)
  }

  return users.filter((user) => !activeUserIds.has(user.id))
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
  participants,
  users,
}) {
  const [userId, setUserId] = useState('')
  const availableUsers = useMemo(
    () => getAvailableUsers(users, participants, game.host_user_id),
    [game.host_user_id, participants, users],
  )

  function handleAddPlayer(event) {
    event.preventDefault()
    onAddPlayer({ userId, reason: '' })
    setUserId('')
  }

  return (
    <section className="admin-official-panel admin-official-roster" aria-label="Official game roster">
      <div className="admin-official-panel__heading">
        <h2>Roster</h2>
        <em>{participants.length}</em>
      </div>

      {canAddPlayer && (
        <form className="admin-official-compact-form admin-official-compact-form--roster" onSubmit={handleAddPlayer}>
          <label className="admin-official-field">
            <span>Add player</span>
            <select required value={userId} onChange={(event) => setUserId(event.target.value)}>
              <option value="">Select user</option>
              {availableUsers.map((user) => (
                <option key={user.id} value={user.id}>
                  {getAdminUserLabel(user)}{user.email ? ` - ${user.email}` : ''}
                </option>
              ))}
            </select>
          </label>
          <button
            className="admin-official-button admin-official-button--primary"
            disabled={isSaving || !userId}
            type="submit"
          >
            <span>Add</span>
          </button>
        </form>
      )}

      <div className="admin-official-roster-list">
        {participants.length === 0 && (
          <p className="admin-official-empty">No roster rows yet.</p>
        )}

        {participants.map((participant) => {
          const removalState = getRemovalState(
            participant,
            game.host_user_id,
            canPreviewRemovals,
          )
          const isPreview = removalState.action === 'preview'
          const isRemove = removalState.action === 'remove'

          return (
            <div className="admin-official-roster-row" key={participant.id}>
              <div>
                <UserIcon />
                <span>
                  <strong>{participant.display_name_snapshot}</strong>
                  <small>{participant.participant_type} / {participant.participant_status}</small>
                </span>
              </div>
              {canManageRoster && (
                <button
                  aria-label={
                    isPreview
                      ? `Preview removal impact for ${participant.display_name_snapshot}`
                      : `Remove ${participant.display_name_snapshot}`
                  }
                  className={[
                    'admin-official-icon-button',
                    isPreview ? 'admin-official-icon-button--preview' : '',
                  ].filter(Boolean).join(' ')}
                  disabled={isSaving || (!isPreview && !isRemove)}
                  title={removalState.title}
                  type="button"
                  onClick={() => {
                    if (isPreview) {
                      onPreviewRemoval(participant)
                    } else if (isRemove) {
                      onRemovePlayer({ participant, reason: '' })
                    }
                  }}
                >
                  {isPreview ? <ClipboardListIcon /> : <TrashIcon />}
                </button>
              )}
            </div>
          )
        })}
      </div>
    </section>
  )
}

export default AdminOfficialGameRosterPanel
