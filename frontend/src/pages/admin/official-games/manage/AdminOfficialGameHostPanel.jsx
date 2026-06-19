import { useMemo, useState } from 'react'
import { UserIcon } from '../../../../components/BrowseIcons.jsx'
import { getAdminUserLabel } from '../shared/adminOfficialGameForm.js'

const eligibleHostParticipantTypes = new Set(['registered_user', 'admin_added'])

function AdminOfficialGameHostPanel({
  canAssignHost,
  canRemoveHost,
  game,
  isSaving,
  onAssignHost,
  onRemoveHost,
  participants,
  users,
}) {
  const [hostUserId, setHostUserId] = useState(game.host_user_id ?? '')
  const currentHost = useMemo(
    () => users.find((user) => user.id === game.host_user_id),
    [game.host_user_id, users],
  )
  const currentHostParticipant = useMemo(
    () => participants.find((participant) => participant.user_id === game.host_user_id),
    [game.host_user_id, participants],
  )
  const currentHostLabel = currentHost
    ? getAdminUserLabel(currentHost)
    : currentHostParticipant?.display_name_snapshot || 'Assigned host'
  const eligibleHostUserIds = useMemo(
    () => new Set(
      participants
        .filter((participant) => (
          participant.participant_status === 'confirmed'
          && eligibleHostParticipantTypes.has(participant.participant_type)
          && participant.user_id
        ))
        .map((participant) => participant.user_id),
    ),
    [participants],
  )
  const eligibleHostUsers = useMemo(
    () => users.filter((user) => eligibleHostUserIds.has(user.id)),
    [eligibleHostUserIds, users],
  )

  function handleAssign(event) {
    event.preventDefault()
    onAssignHost({ hostUserId, reason: '' })
  }

  return (
    <section className="admin-official-panel" aria-label="Official game host">
      <div className="admin-official-panel__heading">
        <h2>Host</h2>
        {game.host_user_id && <em>Assigned</em>}
      </div>

      <div className="admin-official-host-current">
        <UserIcon />
        <strong>{game.host_user_id ? currentHostLabel : 'Unassigned'}</strong>
        {currentHost?.email && <span>{currentHost.email}</span>}
      </div>

      {canAssignHost && (
        <form className="admin-official-compact-form admin-official-host-form" onSubmit={handleAssign}>
          <label className="admin-official-field">
            <span>Host</span>
            <select
              required
              value={hostUserId}
              onChange={(event) => setHostUserId(event.target.value)}
            >
              <option value="">Select user</option>
              {eligibleHostUsers.map((user) => (
                <option key={user.id} value={user.id}>
                  {getAdminUserLabel(user)}{user.email ? ` - ${user.email}` : ''}
                </option>
              ))}
            </select>
          </label>
          <button
            className="admin-official-button admin-official-button--primary"
            disabled={isSaving || !hostUserId}
            type="submit"
          >
            <span>{game.host_user_id ? 'Change host' : 'Assign host'}</span>
          </button>
        </form>
      )}

      {canRemoveHost && (
        <div className="admin-official-button-row admin-official-host-remove">
          <button
            aria-label="Remove host"
            className="admin-official-button admin-official-button--danger"
            disabled={isSaving || !game.host_user_id}
            title="Remove host"
            type="button"
            onClick={() => onRemoveHost('')}
          >
            <span>Remove</span>
          </button>
        </div>
      )}
    </section>
  )
}

export default AdminOfficialGameHostPanel
