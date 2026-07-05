import { useMemo, useState } from 'react'
import { ChevronDownIcon, UserIcon } from '../../../../components/BrowseIcons.jsx'
import AdminOfficialGameSimpleConfirmModal from './AdminOfficialGameSimpleConfirmModal.jsx'

const eligibleHostParticipantTypes = new Set(['registered_user', 'admin_added'])

function getEligibleHostParticipants(participants) {
  const seenUserIds = new Set()
  return participants.filter((participant) => {
    const isEligible = (
      participant.participant_status === 'confirmed'
      && eligibleHostParticipantTypes.has(participant.participant_type)
      && participant.user_id
      && !seenUserIds.has(participant.user_id)
    )
    if (isEligible) {
      seenUserIds.add(participant.user_id)
    }
    return isEligible
  })
}

function AdminOfficialGameHostPanel({
  canAssignHost,
  canRemoveHost,
  game,
  isSaving,
  onAssignHost,
  onRemoveHost,
  participants,
}) {
  const [hostUserId, setHostUserId] = useState(game.host_user_id ?? '')
  const [pendingHostParticipant, setPendingHostParticipant] = useState(null)
  const [isRemoveHostConfirmOpen, setIsRemoveHostConfirmOpen] = useState(false)
  const currentHostParticipant = useMemo(
    () => participants.find((participant) =>
      participant.user_id === game.host_user_id
      && participant.participant_status === 'confirmed',
    ),
    [game.host_user_id, participants],
  )
  const eligibleHostParticipants = useMemo(
    () => getEligibleHostParticipants(participants),
    [participants],
  )
  const selectedHostParticipant = eligibleHostParticipants.find(
    (participant) => participant.user_id === hostUserId,
  )
  const currentHostLabel = currentHostParticipant?.display_name_snapshot || 'No host assigned'

  function handleAssign(event) {
    event.preventDefault()
    if (!selectedHostParticipant || selectedHostParticipant.user_id === game.host_user_id) {
      return
    }

    setPendingHostParticipant(selectedHostParticipant)
  }

  async function handleConfirmAssignHost() {
    if (!pendingHostParticipant?.user_id) {
      return
    }

    const didAssign = await onAssignHost({
      hostUserId: pendingHostParticipant.user_id,
      reason: '',
    })
    if (didAssign) {
      setPendingHostParticipant(null)
    }
  }

  async function handleConfirmRemoveHost() {
    const didRemove = await onRemoveHost('')
    if (didRemove) {
      setIsRemoveHostConfirmOpen(false)
    }
  }

  return (
    <>
      <section
        className="admin-official-panel admin-official-host"
        aria-label="Official game host"
      >
        <div className="admin-official-panel__heading">
          <div className="admin-official-panel-title">
            <UserIcon />
            <h2>Host</h2>
          </div>
        </div>

        <div className="admin-official-host-current">
          <span>Current host</span>
          <strong>{currentHostLabel}</strong>
        </div>

        <div className="admin-official-host-controls">
          {canAssignHost && (
            <form
              className="admin-official-compact-form admin-official-host-form"
              onSubmit={handleAssign}
            >
              <label className="admin-official-field">
                <span>Change host</span>
                <span className="admin-official-host-select">
                  <select
                    required
                    value={hostUserId}
                    onChange={(event) => setHostUserId(event.target.value)}
                  >
                    <option value="">Select roster player</option>
                    {eligibleHostParticipants.map((participant) => (
                      <option key={participant.id} value={participant.user_id}>
                        {participant.display_name_snapshot}
                      </option>
                    ))}
                  </select>
                  <ChevronDownIcon />
                </span>
              </label>
              <button
                className="admin-official-button admin-official-button--primary"
                disabled={isSaving || !hostUserId || hostUserId === game.host_user_id}
                type="submit"
              >
                <span>Assign host</span>
              </button>
            </form>
          )}

          {canRemoveHost && (
            <div className="admin-official-button-row admin-official-host-remove">
              <button
                aria-label="Remove host"
                className="admin-official-button admin-official-button--danger-solid"
                disabled={isSaving || !game.host_user_id}
                title="Remove host"
                type="button"
                onClick={() => setIsRemoveHostConfirmOpen(true)}
              >
                <span>Remove host</span>
              </button>
            </div>
          )}
        </div>
      </section>

      {pendingHostParticipant && (
        <AdminOfficialGameSimpleConfirmModal
          confirmLabel="Assign host"
          isSaving={isSaving}
          title={`Assign ${pendingHostParticipant.display_name_snapshot} as host?`}
          onClose={() => setPendingHostParticipant(null)}
          onConfirm={handleConfirmAssignHost}
        />
      )}

      {isRemoveHostConfirmOpen && (
        <AdminOfficialGameSimpleConfirmModal
          confirmLabel="Remove host"
          isSaving={isSaving}
          title="Remove host?"
          variant="danger"
          onClose={() => setIsRemoveHostConfirmOpen(false)}
          onConfirm={handleConfirmRemoveHost}
        />
      )}
    </>
  )
}

export default AdminOfficialGameHostPanel
