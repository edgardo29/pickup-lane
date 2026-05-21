import {
  formatNeedLabel,
  getRequesterInitials,
  getRequesterName,
} from './needASubFormatters.js'

export function NeedASubPlayerPanel({
  activeStatus,
  group,
  onAccept,
  onDecline,
  onRemove,
  onStatusChange,
  onViewWaitlist,
}) {
  const selectedLabel = formatNeedLabel(group.position).replace(/^\d+\s+Subs?\s+·\s+/, '')
  const statusTabs = [
    { id: 'pending', label: 'Pending', count: group.pending.length },
    { id: 'confirmed', label: 'Confirmed', count: group.confirmed.length },
    { id: 'waitlist', label: 'Waitlist', count: group.waitlisted.length },
  ]
  const activeRequests = {
    pending: group.pending,
    confirmed: group.confirmed,
    waitlist: group.waitlisted,
  }[activeStatus] || []

  return (
    <section className="need-sub-manage-card need-sub-player-panel">
      <header className="need-sub-player-panel__header">
        <div>
          <h2>Requests</h2>
          <strong>{selectedLabel}</strong>
        </div>
      </header>

      <div className="need-sub-request-tabs" role="tablist" aria-label="Request status">
        {statusTabs.map((tab) => (
          <button
            aria-selected={activeStatus === tab.id}
            className={activeStatus === tab.id ? 'need-sub-request-tabs__tab--active' : ''}
            key={tab.id}
            role="tab"
            type="button"
            onClick={() => onStatusChange(tab.id)}
          >
            <span>{tab.label}</span>
            <strong>{tab.count}</strong>
          </button>
        ))}
      </div>

      <PlayerSection
        onViewWaitlist={onViewWaitlist}
        requests={activeRequests}
        status={activeStatus}
        waitlistTotal={group.waitlisted.length}
        renderActions={(request) => {
          if (activeStatus === 'pending') {
            return (
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
            )
          }

          if (activeStatus === 'confirmed') {
            return (
              <button
                className="need-sub-secondary-action"
                type="button"
                onClick={() => onRemove(request)}
              >
                Remove
              </button>
            )
          }

          return null
        }}
      />
    </section>
  )
}

function PlayerSection({
  onViewWaitlist = null,
  renderActions = null,
  requests,
  status,
  waitlistTotal = 0,
}) {
  const isWaitlist = status === 'waitlist'
  const emptyText = {
    pending: 'No pending requests',
    confirmed: 'No confirmed players',
    waitlist: 'No waitlisted players',
  }[status] || 'No requests'

  if (!requests.length) {
    return (
      <section className="need-sub-player-section need-sub-player-section--empty">
        <div className="need-sub-manage-empty need-sub-manage-empty--center">
          {emptyText}
        </div>
      </section>
    )
  }

  return (
    <section className="need-sub-player-section">
      <div className="need-sub-manage-request-list">
        {requests.map((request, index) => (
          <PlayerRow
            key={request.id}
            request={request}
            status={status}
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

function PlayerRow({ renderActions, request, status, waitlistPosition = null }) {
  const detailText = status === 'waitlist' && waitlistPosition
    ? `#${waitlistPosition} on waitlist`
    : ''
  const actions = renderActions?.(request)

  return (
    <div className={`need-sub-manage-request ${actions ? '' : 'need-sub-manage-request--static'}`}>
      <span className="need-sub-manage-request__avatar" aria-hidden="true">
        {getRequesterInitials(request)}
      </span>
      <div>
        <strong>{getRequesterName(request)}</strong>
        {detailText && <span>{detailText}</span>}
      </div>
      {actions && (
        <div className="need-sub-manage-request__actions">
          {actions}
        </div>
      )}
    </div>
  )
}
