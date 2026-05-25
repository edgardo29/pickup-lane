import { useMemo, useState } from 'react'
import { TrashIcon, UserIcon } from '../../../../components/BrowseIcons.jsx'
import { getAdminUserLabel } from '../shared/adminOfficialGameForm.js'

const removableStatuses = new Set(['confirmed', 'pending_payment'])

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
  game,
  isSaving,
  onAddPlayer,
  onRemovePlayer,
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

      <div className="admin-official-roster-list">
        {participants.length === 0 && (
          <p className="admin-official-empty">No roster rows yet.</p>
        )}

        {participants.map((participant) => {
          const canRemove = removableStatuses.has(participant.participant_status)
            && participant.participant_type !== 'host'

          return (
            <div className="admin-official-roster-row" key={participant.id}>
              <div>
                <UserIcon />
                <span>
                  <strong>{participant.display_name_snapshot}</strong>
                  <small>{participant.participant_type} / {participant.participant_status}</small>
                </span>
              </div>
              <button
                aria-label={`Remove ${participant.display_name_snapshot}`}
                className="admin-official-icon-button"
                disabled={isSaving || !canRemove}
                title={canRemove ? 'Remove player' : 'This roster row uses a different removal flow'}
                type="button"
                onClick={() => onRemovePlayer({ participant, reason: '' })}
              >
                <TrashIcon />
              </button>
            </div>
          )
        })}
      </div>
    </section>
  )
}

export default AdminOfficialGameRosterPanel
