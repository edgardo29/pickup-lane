import { ClipboardListIcon } from '../../../../components/BrowseIcons.jsx'
import AdminOfficialGameEmptyState from './AdminOfficialGameEmptyState.jsx'
import {
  formatAdminDateTime,
  getTitleLabel,
} from './adminOfficialGameManageDisplay.js'

function ActivityFact({ label, meta, value }) {
  return (
    <div className="admin-booking-card__fact">
      <span>{label}</span>
      <strong>{value}</strong>
      {meta && <small>{meta}</small>}
    </div>
  )
}

function getShortId(value, fallback = 'Unknown') {
  return value ? String(value).slice(0, 8) : fallback
}

function getParticipantEmail(participant) {
  return participant?.user_email || participant?.guest_email || ''
}

function getParticipantByUserId(userId, participants) {
  if (!userId) {
    return null
  }

  return participants.find((item) => item.user_id === userId) || null
}

function getPlayerAffected(action, participants) {
  if (action.target_user_id) {
    const participant = getParticipantByUserId(action.target_user_id, participants)
    return {
      email: getParticipantEmail(participant) || action.target_user_email || '',
      name:
        participant?.display_name_snapshot ||
        action.target_user_display_name ||
        `User ${getShortId(action.target_user_id)}`,
    }
  }

  if (action.target_participant_id) {
    const participant = participants.find((item) => item.id === action.target_participant_id)
    return {
      email: getParticipantEmail(participant),
      name: participant?.display_name_snapshot || `Participant ${getShortId(action.target_participant_id)}`,
    }
  }

  return {
    email: '',
    name: 'No player target',
  }
}

function getChangedBy(action, participants) {
  const participant = getParticipantByUserId(action.admin_user_id, participants)
  return {
    email: action.admin_user_email || getParticipantEmail(participant),
    name:
      action.admin_user_display_name ||
      participant?.display_name_snapshot ||
      `Admin ${getShortId(action.admin_user_id)}`,
  }
}

function AdminOfficialGameAuditTab({ actions, error, loadState, participants }) {
  return (
    <section className="admin-manage-tab-panel admin-bookings-panel" aria-label="Official game activity">
      <div className="admin-manage-panel-heading admin-bookings-heading">
        <div className="admin-bookings-heading__copy">
          <span className="admin-bookings-heading__icon">
            <ClipboardListIcon />
          </span>
          <div>
            <h2>Activity</h2>
            <p>Track official game changes and staff actions.</p>
          </div>
        </div>
      </div>

      {error && <p className="admin-official-alert">{error}</p>}
      {loadState === 'loading' && (
        <p className="admin-official-empty">Loading activity.</p>
      )}

      {loadState === 'ready' && (
        actions.length === 0 ? (
          <AdminOfficialGameEmptyState
            icon={ClipboardListIcon}
            title="No activity yet"
          >
            Official game changes and staff actions will appear here.
          </AdminOfficialGameEmptyState>
        ) : (
          <div className="admin-booking-card-grid" aria-label="Activity actions">
            {actions.map((action) => {
              const actionId = getShortId(action.id)
              const changedBy = getChangedBy(action, participants)
              const playerAffected = getPlayerAffected(action, participants)

              return (
                <article className="admin-booking-card admin-activity-card" key={action.id}>
                  <header className="admin-booking-card__header">
                    <div className="admin-booking-card__buyer">
                      <ClipboardListIcon />
                      <span>
                        <small>Action</small>
                        <strong>{getTitleLabel(action.action_type)}</strong>
                      </span>
                    </div>
                  </header>

                  <div className="admin-booking-card__facts">
                    <ActivityFact
                      label="Player affected"
                      meta={playerAffected.email}
                      value={playerAffected.name}
                    />
                    <ActivityFact
                      label="Changed by"
                      meta={changedBy.email}
                      value={changedBy.name}
                    />
                    <ActivityFact
                      label="When"
                      value={formatAdminDateTime(action.created_at)}
                    />
                    <ActivityFact label="Log reference" value={actionId} />
                  </div>
                </article>
              )
            })}
          </div>
        )
      )}
    </section>
  )
}

export default AdminOfficialGameAuditTab
