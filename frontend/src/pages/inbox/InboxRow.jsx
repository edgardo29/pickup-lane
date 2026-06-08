import { formatNotificationDate, formatRelativeTime } from './inboxFormatters.js'
import InboxNotificationIcon from './InboxNotificationIcon.jsx'

function InboxRow({ notification, onOpenNotification }) {
  const eventAt = notification.event_at || notification.created_at
  const relativeTime = formatRelativeTime(eventAt)
  const sourceLabel = notification.source_label || 'Pickup Lane'
  const title = notification.title || 'Inbox update'
  const rowSubject = notification.row_subject || notification.subject_label || 'Pickup Lane'

  return (
    <button
      className={`inbox-row ${notification.is_read ? '' : 'inbox-row--unread'}`}
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
          {!notification.is_read && <em>New</em>}
        </span>
        <span className="inbox-row__subject">{rowSubject}</span>
      </span>

      <span className="inbox-row__meta">
        <span className="inbox-row__time">{relativeTime}</span>
        <span className="inbox-row__date">{formatNotificationDate(eventAt)}</span>
        <span className="inbox-row__read-indicator" aria-hidden="true" />
      </span>
    </button>
  )
}

export default InboxRow
