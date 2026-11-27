import { useEffect, useRef } from 'react'
import { X } from 'lucide-react'
import { getRenderableNotificationAction } from './inboxData.js'
import {
  formatNotificationDateTime,
  formatSubjectDateTime,
} from './inboxFormatters.js'
import InboxNotificationIcon from './InboxNotificationIcon.jsx'

function NotificationModal({ notification, onClose, onNotificationAction }) {
  const closeButtonRef = useRef(null)
  const dialogRef = useRef(null)
  const onCloseRef = useRef(onClose)
  const action = getRenderableNotificationAction(notification)
  const actionDisabled = Boolean(action?.disabled)
  const eventAt = notification.occurred_at || notification.event_at || notification.created_at
  const notificationTime = formatNotificationDateTime(eventAt)
  const sourceLabel = notification.source_label || 'Pickup Lane'
  const title = notification.title || 'Inbox update'
  const subjectLabel = notification.subject_label || sourceLabel
  const showSubject = Boolean(
    notification.subject_label &&
      notification.subject_label !== sourceLabel &&
      notification.item_kind !== 'platform_notice',
  )
  const subjectTime = formatSubjectDateTime(
    notification.subject_starts_at,
    notification.subject_timezone,
  )
  const body = notification.message || notification.body || 'Open this update for more details.'

  useEffect(() => {
    onCloseRef.current = onClose
  }, [onClose])

  useEffect(() => {
    const previouslyFocused = document.activeElement
    closeButtonRef.current?.focus()

    function handleDialogKeyDown(event) {
      if (event.key === 'Escape') {
        onCloseRef.current()
        return
      }

      if (event.key !== 'Tab') {
        return
      }

      const focusable = Array.from(dialogRef.current?.querySelectorAll(
        'button:not(:disabled), [href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])',
      ) || [])
      if (focusable.length === 0) {
        event.preventDefault()
        return
      }

      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      if (
        event.shiftKey &&
        (document.activeElement === first || !dialogRef.current?.contains(document.activeElement))
      ) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }

    window.addEventListener('keydown', handleDialogKeyDown)
    return () => {
      window.removeEventListener('keydown', handleDialogKeyDown)
      if (previouslyFocused?.isConnected) {
        previouslyFocused.focus()
      } else {
        const fallback = document.querySelector('.inbox-tab-panel select') ||
          document.querySelector('[role="tab"][aria-selected="true"]')
        fallback?.focus()
      }
    }
  }, [])

  return (
    <div className="inbox-modal-backdrop" role="presentation" onClick={onClose}>
      <section
        ref={dialogRef}
        className="inbox-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="inbox-modal-title"
        onClick={(event) => event.stopPropagation()}
      >
        <button ref={closeButtonRef} className="inbox-modal__close" type="button" onClick={onClose} aria-label="Close">
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

        {showSubject && (
          <p className="inbox-modal__subject">
            <strong>{subjectLabel}</strong>
            {subjectTime && <span>{subjectTime}</span>}
          </p>
        )}

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
                disabled={actionDisabled}
                type="button"
                onClick={() => {
                  if (!actionDisabled) {
                    onNotificationAction(action)
                  }
                }}
              >
                {action.label}
              </button>
            )}
          </div>
          {actionDisabled && action.disabled_reason && (
            <p className="inbox-modal__action-note">{action.disabled_reason}</p>
          )}
        </div>
      </section>
    </div>
  )
}

export default NotificationModal
