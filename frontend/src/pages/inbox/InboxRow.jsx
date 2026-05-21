import { GAME_ACTIVITY_TYPES } from './inboxData.js'
import { formatRelativeTime } from './inboxFormatters.js'

function InboxRow({ game, notification, onOpenNotification }) {
  const isGameActivity = GAME_ACTIVITY_TYPES.has(notification.notification_type)
  const title = isGameActivity && game ? game.title : notification.title

  return (
    <button
      className={`inbox-row ${notification.is_read ? '' : 'inbox-row--unread'}`}
      type="button"
      onClick={() => onOpenNotification(notification)}
    >
      <span className="inbox-row__body">
        <span className="inbox-row__titleline">
          <strong>{title}</strong>
          {!notification.is_read && <em>New</em>}
        </span>
        <span>{notification.body}</span>
      </span>

      <span className="inbox-row__meta">
        {formatRelativeTime(notification.created_at)}
        <i aria-hidden="true" />
      </span>
    </button>
  )
}

export default InboxRow
