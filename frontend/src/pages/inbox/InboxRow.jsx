import { formatNotificationDate, formatRelativeTime } from './inboxFormatters.js'
import InboxNotificationIcon from './InboxNotificationIcon.jsx'
import { isInboxItemNew } from './inboxData.js'

function InboxRow({
  notification,
  onOpenNotification,
  showMeta = true,
  showNewBadge = true,
  showReadIndicator = true,
  showRelativeTime = true,
  showUnreadState = true,
}) {
  const eventAt = notification.occurred_at || notification.event_at || notification.created_at
  const relativeTime = showRelativeTime ? formatRelativeTime(eventAt) : ''
  const sourceLabel = notification.source_label || 'Pickup Lane'
  const title = notification.title || 'Inbox update'
  const rowSubject = notification.row_subject || notification.subject_label || ''
  const isNew = showUnreadState && isInboxItemNew(notification)
  const isDateOnlyMeta = showMeta && !showRelativeTime && !showReadIndicator
  const rowClassName = [
    'inbox-row',
    isNew ? 'inbox-row--unread' : '',
    showMeta ? '' : 'inbox-row--without-meta',
  ].filter(Boolean).join(' ')

  return (
    <button
      className={rowClassName}
      type="button"
      onClick={() => onOpenNotification(notification)}
    >
      <InboxNotificationIcon
        className="inbox-row__icon"
        notification={notification}
      />

      <span className="inbox-row__body">
        <span className="inbox-row__titleline">
          <span className="inbox-row__source">[{sourceLabel}]</span>
          <strong>{title}</strong>
          {showNewBadge && isNew && <em>New</em>}
        </span>
        {rowSubject && <span className="inbox-row__subject">{rowSubject}</span>}
      </span>

      {showMeta && (
        <span className={`inbox-row__meta ${isDateOnlyMeta ? 'inbox-row__meta--date-only' : ''}`}>
          {showRelativeTime && <span className="inbox-row__time">{relativeTime}</span>}
          <span className="inbox-row__date">{formatNotificationDate(eventAt)}</span>
          {showReadIndicator && (
            <span className="inbox-row__read-indicator" aria-hidden="true" />
          )}
        </span>
      )}
    </button>
  )
}

export default InboxRow
