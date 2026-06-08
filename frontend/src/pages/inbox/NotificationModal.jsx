import { X } from 'lucide-react'
import { getNotificationAction } from './inboxData.js'
import {
  formatNotificationDateTime,
  formatSubjectDateTime,
} from './inboxFormatters.js'
import InboxNotificationIcon from './InboxNotificationIcon.jsx'

function NotificationModal({ notification, onClose, onNotificationAction }) {
  const action = getNotificationAction(notification)
  const eventAt = notification.event_at || notification.created_at
  const notificationTime = formatNotificationDateTime(eventAt)
  const sourceLabel = notification.source_label || 'Pickup Lane'
  const title = notification.title || 'Inbox update'
  const subjectLabel = notification.subject_label || sourceLabel
  const subjectTime = formatSubjectDateTime(
    notification.subject_starts_at,
    notification.subject_timezone,
  )
  const body = notification.body || 'Open this update for more details.'

  return (
    <div className="inbox-modal-backdrop" role="presentation" onClick={onClose}>
      <section
        className="inbox-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="inbox-modal-title"
        onClick={(event) => event.stopPropagation()}
      >
        <button className="inbox-modal__close" type="button" onClick={onClose} aria-label="Close">
          <X aria-hidden="true" />
        </button>

        <div className="inbox-modal__header">
          <InboxNotificationIcon
            className="inbox-modal__icon"
            notification={notification}
          />
          <div className="inbox-modal__heading-copy">
            <span className="inbox-modal__source-label">[{sourceLabel}]</span>
            <h2 id="inbox-modal-title">{title}</h2>
          </div>
        </div>

        <p className="inbox-modal__subject">
          <strong>{subjectLabel}</strong>
          {subjectTime && <span>{subjectTime}</span>}
        </p>

        <div className="inbox-modal__message">
          <span>Message</span>
          <p>{body}</p>
        </div>

        <div className="inbox-modal__footer">
          {notificationTime && (
            <time className="inbox-modal__timestamp">{notificationTime}</time>
          )}

          <div className="inbox-modal__actions">
            <button className="inbox-modal__secondary" type="button" onClick={onClose}>
              Back
            </button>

            {action && (
              <button
                className="inbox-modal__primary"
                type="button"
                onClick={() => onNotificationAction(action)}
              >
                {action.label}
              </button>
            )}
          </div>
        </div>
      </section>
    </div>
  )
}

export default NotificationModal
