import { formatFullDate } from './inboxFormatters.js'

function NotificationModal({ game, notification, onClose, onViewGame }) {
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
          ×
        </button>

        <p className="inbox-modal__meta">{formatFullDate(notification.created_at)}</p>
        <h2 id="inbox-modal-title">{notification.title}</h2>
        <p>{notification.body}</p>

        {game && (
          <button
            className="inbox-modal__action"
            type="button"
            onClick={() => onViewGame(game.id)}
          >
            View game
          </button>
        )}
      </section>
    </div>
  )
}

export default NotificationModal
