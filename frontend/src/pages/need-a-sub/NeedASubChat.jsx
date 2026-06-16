import { createPortal } from 'react-dom'
import { MessageSquareText, Send, X } from 'lucide-react'
import {
  dismissNeedASubBackdropMouseDown,
  useNeedASubModalDismiss,
} from './useNeedASubModalDismiss.js'

export function NeedASubChatSection({
  canOpen,
  disabledReason,
  isOpening,
  onOpen,
  unreadCount,
}) {
  const hasUnread = Number(unreadCount || 0) > 0
  const sectionClassName = [
    'need-sub-chat-section',
    hasUnread ? 'need-sub-chat-section--unread' : '',
  ].filter(Boolean).join(' ')

  return (
    <div className={sectionClassName}>
      <div className="need-sub-chat-section__copy">
        <span className="need-sub-chat-section__heading">
          <MessageSquareText aria-hidden="true" />
          <span>Sub chat</span>
          {hasUnread && <em>New</em>}
        </span>
        <p>
          {canOpen
            ? 'Coordinate game-day details with the group.'
            : disabledReason}
        </p>
      </div>

      <button
        className="need-sub-chat-section__button"
        disabled={!canOpen || isOpening}
        type="button"
        onClick={onOpen}
      >
        <MessageSquareText aria-hidden="true" />
        <span>
          {isOpening ? 'Opening...' : 'Open Chat'}
          {hasUnread && !isOpening && <i aria-hidden="true" />}
        </span>
      </button>
    </div>
  )
}

export function NeedASubChatModal({
  currentUserId,
  draft,
  error,
  hasMoreMessages,
  isLoadingOlder,
  isSending,
  maxLength,
  messages,
  onChangeDraft,
  onClose,
  onLoadOlder,
  onSend,
}) {
  const remainingCharacters = maxLength - draft.length

  useNeedASubModalDismiss(onClose)

  return createPortal(
    <div
      className="need-sub-modal-backdrop"
      role="presentation"
      onMouseDown={(event) => dismissNeedASubBackdropMouseDown(event, onClose)}
    >
      <section
        aria-labelledby="need-sub-chat-title"
        aria-modal="true"
        className="need-sub-chat-modal"
        role="dialog"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="need-sub-chat-modal__header">
          <h2 id="need-sub-chat-title">
            <span>
              <MessageSquareText aria-hidden="true" />
            </span>
            Sub Chat
          </h2>
          <button
            className="need-sub-modal-close need-sub-chat-modal__close"
            type="button"
            aria-label="Close chat"
            onClick={onClose}
          >
            <X aria-hidden="true" />
          </button>
        </header>

        <div
          className={[
            'need-sub-chat-modal__thread',
            messages.length === 0 ? 'need-sub-chat-modal__thread--empty' : '',
          ].filter(Boolean).join(' ')}
        >
          {hasMoreMessages && (
            <button
              className="need-sub-chat-modal__load-older"
              disabled={isLoadingOlder}
              type="button"
              onClick={onLoadOlder}
            >
              {isLoadingOlder ? 'Loading...' : 'Load older'}
            </button>
          )}

          {messages.length > 0 ? (
            messages.map((message) => (
              <NeedASubChatMessage
                currentUserId={currentUserId}
                key={message.id}
                message={message}
              />
            ))
          ) : (
            <p className="need-sub-chat-modal__empty">No messages yet.</p>
          )}
        </div>

        <form className="need-sub-chat-composer" onSubmit={onSend}>
          <label htmlFor="need-sub-chat-message">Message</label>
          <textarea
            id="need-sub-chat-message"
            maxLength={maxLength}
            placeholder="Type a message"
            rows={2}
            value={draft}
            onChange={(event) => onChangeDraft(event.target.value)}
          />
          <div className="need-sub-chat-composer__footer">
            <span className={remainingCharacters < 30 ? 'warn' : ''}>
              {draft.length}/{maxLength}
            </span>
            <button type="submit" disabled={isSending || !draft.trim()}>
              <Send aria-hidden="true" />
              {isSending ? 'Sending...' : 'Send'}
            </button>
          </div>
          {error && <p className="need-sub-chat-error">{error}</p>}
        </form>
      </section>
    </div>,
    document.body,
  )
}

function NeedASubChatMessage({ currentUserId, message }) {
  const isOwn = currentUserId && message.sender_user_id === currentUserId
  const senderName = message.sender_display_name_snapshot || 'Pickup Lane Player'
  const senderStatusLabel = message.sender_status_label
  const senderInitials = message.sender_initials_snapshot || getInitials(senderName) || 'PL'

  return (
    <article
      className={[
        'need-sub-chat-message',
        isOwn ? 'need-sub-chat-message--own' : '',
      ].filter(Boolean).join(' ')}
    >
      <span>{senderInitials}</span>
      <div>
        <header>
          <strong>{isOwn ? 'You' : senderName}</strong>
          {senderStatusLabel && <em>{senderStatusLabel}</em>}
          <small>{formatRelativeTime(message.created_at)}</small>
        </header>
        <p>{message.message_body}</p>
      </div>
    </article>
  )
}

function getInitials(value) {
  return String(value || '')
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase()
}

function formatRelativeTime(value) {
  if (!value) {
    return 'Just now'
  }

  const minutes = Math.max(1, Math.round((Date.now() - new Date(value)) / 60000))

  if (minutes < 60) {
    return `${minutes}m ago`
  }

  const hours = Math.round(minutes / 60)
  if (hours < 24) {
    return `${hours}h ago`
  }

  const days = Math.round(hours / 24)
  return `${days}d ago`
}
