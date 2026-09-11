import { ClipboardListIcon } from '../../../../components/BrowseIcons.jsx'
import AdminOfficialGameEmptyState from './AdminOfficialGameEmptyState.jsx'
import { formatAdminDateTime } from './adminOfficialGameManageDisplay.js'

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

function AdminOfficialGameAuditTab({ actions, error, loadState }) {
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

              return (
                <article className="admin-booking-card admin-activity-card" key={action.id}>
                  <header className="admin-booking-card__header">
                    <div className="admin-booking-card__buyer">
                      <ClipboardListIcon />
                      <span>
                        <small>Action</small>
                        <strong>{action.action_label}</strong>
                      </span>
                    </div>
                  </header>

                  <div className="admin-booking-card__facts">
                    <ActivityFact
                      label="Target"
                      value={action.target_label}
                    />
                    <ActivityFact
                      label="Changed by"
                      value={action.admin_label}
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
