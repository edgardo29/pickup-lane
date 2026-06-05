import { CheckCircle2, ClipboardList, Clock3, UsersRound } from 'lucide-react'
import { getRequesterInitials, getRequesterName } from './needASubFormatters.js'

export function NeedASubPlayerPanel({
  activeStatus,
  group,
  onAccept,
  onDecline,
  onRemove,
  onStatusChange,
  onViewWaitlist,
}) {
  const statusTabs = [
    { id: 'pending', label: 'Pending', count: group.pending.length, Icon: Clock3 },
    { id: 'confirmed', label: 'Confirmed', count: group.confirmed.length, Icon: CheckCircle2 },
    { id: 'waitlist', label: 'Waitlist', count: group.waitlisted.length, Icon: UsersRound },
  ]
  const activeRequests = {
    pending: group.pending,
    confirmed: group.confirmed,
    waitlist: group.waitlisted,
  }[activeStatus] || []

  return (
    <section className="need-sub-manage-card need-sub-player-panel">
      <header className="need-sub-player-panel__header">
        <h2>
          <ClipboardList aria-hidden="true" />
          Requests
        </h2>
      </header>

      <div className="need-sub-request-tabs" role="tablist" aria-label="Request status">
        {statusTabs.map((tab) => {
          const TabIcon = tab.Icon

          return (
            <button
              aria-selected={activeStatus === tab.id}
              className={activeStatus === tab.id ? 'need-sub-request-tabs__tab--active' : ''}
              key={tab.id}
              role="tab"
              type="button"
              onClick={() => onStatusChange(tab.id)}
            >
              <TabIcon aria-hidden="true" />
              <span>{tab.label}</span>
              <strong>{tab.count}</strong>
            </button>
          )
        })}
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
                <button
                  className="need-sub-manage-request__action need-sub-manage-request__action--primary"
                  type="button"
                  onClick={() => onAccept(request)}
                >
                  Accept
                </button>
                <button
                  className="need-sub-manage-request__action need-sub-secondary-action"
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
                className="need-sub-manage-request__action need-sub-secondary-action"
                type="button"
                onClick={() => onRemove(request)}
              >
                Remove
              </button>
            )
          }

          if (activeStatus === 'waitlist') {
            return (
              <button
                className="need-sub-manage-request__action need-sub-secondary-action"
                type="button"
                onClick={() => onDecline(request)}
              >
                Decline
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
        {requests.map((request) => (
          <PlayerRow
            key={request.id}
            request={request}
            renderActions={renderActions}
          />
        ))}
      </div>
      {requests.length > 1 && (
        <p className="need-sub-player-section__count">
          {buildRequestCountText(status, requests.length)}
        </p>
      )}
      {isWaitlist && waitlistTotal > requests.length && (
        <button className="need-sub-waitlist-link" type="button" onClick={onViewWaitlist}>
          View all {waitlistTotal} waitlisted
        </button>
      )}
    </section>
  )
}

function PlayerRow({ renderActions, request }) {
  const actions = renderActions?.(request)

  return (
    <div className={`need-sub-manage-request ${actions ? '' : 'need-sub-manage-request--static'}`}>
      <span className="need-sub-manage-request__avatar" aria-hidden="true">
        {getRequesterInitials(request)}
      </span>
      <div>
        <strong>{getRequesterName(request)}</strong>
      </div>
      {actions && (
        <div className="need-sub-manage-request__actions">
          {actions}
        </div>
      )}
    </div>
  )
}

function buildRequestCountText(status, count) {
  const labels = {
    pending: count === 1 ? 'pending request' : 'pending requests',
    confirmed: count === 1 ? 'confirmed player' : 'confirmed players',
    waitlist: count === 1 ? 'waitlisted player' : 'waitlisted players',
  }

  return `Showing ${count} ${labels[status] || 'requests'}`
}
