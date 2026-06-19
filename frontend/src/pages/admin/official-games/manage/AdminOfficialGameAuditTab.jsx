import {
  formatAdminDateTime,
  getAuditRelatedTargetLabel,
  getTitleLabel,
} from './adminOfficialGameManageDisplay.js'

function AdminOfficialGameAuditTab({ actions, error, loadState }) {
  const latestAction = actions[0]
  const uniqueActionTypeCount = new Set(actions.map((action) => action.action_type)).size
  const uniqueAdminCount = new Set(actions.map((action) => action.admin_user_id)).size

  return (
    <section className="admin-official-panel admin-manage-tab-panel" aria-label="Official game audit log">
      <div className="admin-manage-panel-heading">
        <div>
          <h2>Audit</h2>
          <p>Read-only action history for this official game.</p>
        </div>
        <strong>{actions.length}</strong>
      </div>

      <div className="admin-bookings-summary" aria-label="Audit summary">
        <div>
          <span>Loaded actions</span>
          <strong>{actions.length}</strong>
        </div>
        <div>
          <span>Action types</span>
          <strong>{uniqueActionTypeCount}</strong>
        </div>
        <div>
          <span>Staff users</span>
          <strong>{uniqueAdminCount}</strong>
        </div>
        <div>
          <span>Latest</span>
          <strong>{latestAction ? formatAdminDateTime(latestAction.created_at) : 'None'}</strong>
        </div>
      </div>

      {error && <p className="admin-official-alert">{error}</p>}
      {loadState === 'loading' && (
        <p className="admin-official-empty">Loading audit actions.</p>
      )}
      {loadState === 'ready' && actions.length === 0 && (
        <p className="admin-official-empty">No audit actions yet.</p>
      )}

      {loadState === 'ready' && actions.length > 0 && (
        <div className="admin-bookings-table admin-money-table" role="table" aria-label="Audit actions">
          <div className="admin-bookings-table__header" role="row">
            <span role="columnheader">Action</span>
            <span role="columnheader">Related target</span>
            <span role="columnheader">Admin</span>
            <span role="columnheader">Reason</span>
            <span role="columnheader">Created</span>
          </div>
          {actions.map((action) => (
            <div key={action.id} className="admin-bookings-table__row" role="row">
              <div data-label="Action" role="cell">
                <strong>{getTitleLabel(action.action_type)}</strong>
                <span>{String(action.id).slice(0, 8)}</span>
              </div>
              <div data-label="Related target" role="cell">
                <strong>{getAuditRelatedTargetLabel(action)}</strong>
                <span>
                  {action.target_game_id
                    ? `Game ${String(action.target_game_id).slice(0, 8)}`
                    : 'No game target'}
                </span>
              </div>
              <div data-label="Admin" role="cell">
                <strong>{String(action.admin_user_id).slice(0, 8)}</strong>
                <span>Staff actor</span>
              </div>
              <div data-label="Reason" role="cell">
                <strong>{action.reason || 'No reason'}</strong>
                <span>{action.idempotency_key || 'No idempotency key'}</span>
              </div>
              <div data-label="Created" role="cell">
                <strong>{formatAdminDateTime(action.created_at)}</strong>
                <span>Action timestamp</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}

export default AdminOfficialGameAuditTab
