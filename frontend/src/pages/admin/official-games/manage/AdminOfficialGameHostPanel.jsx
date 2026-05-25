import { useMemo, useState } from 'react'
import { UserIcon } from '../../../../components/BrowseIcons.jsx'
import { getAdminUserLabel } from '../shared/adminOfficialGameForm.js'

function AdminOfficialGameHostPanel({
  game,
  isSaving,
  onAssignHost,
  onRemoveHost,
  users,
}) {
  const [hostUserId, setHostUserId] = useState(game.host_user_id ?? '')
  const currentHost = useMemo(
    () => users.find((user) => user.id === game.host_user_id),
    [game.host_user_id, users],
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
        <strong>{game.host_user_id ? getAdminUserLabel(currentHost) : 'Unassigned'}</strong>
        {currentHost?.email && <span>{currentHost.email}</span>}
      </div>

      <form className="admin-official-compact-form admin-official-host-form" onSubmit={handleAssign}>
        <label className="admin-official-field">
          <span>Host</span>
          <select
            required
            value={hostUserId}
            onChange={(event) => setHostUserId(event.target.value)}
          >
            <option value="">Select user</option>
            {users.map((user) => (
              <option key={user.id} value={user.id}>
                {getAdminUserLabel(user)}{user.email ? ` - ${user.email}` : ''}
              </option>
            ))}
          </select>
        </label>
        <div className="admin-official-button-row">
          <button
            className="admin-official-button admin-official-button--primary"
            disabled={isSaving || !hostUserId}
            type="submit"
          >
            <span>{game.host_user_id ? 'Change host' : 'Assign host'}</span>
          </button>
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
      </form>
    </section>
  )
}

export default AdminOfficialGameHostPanel
