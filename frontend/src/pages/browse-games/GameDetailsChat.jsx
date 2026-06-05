import { MessageSquare } from 'lucide-react'
import { getInitials } from './gameDetailsFormatters.js'
import { InfoCard } from './GameDetailsPrimitives.jsx'

export function GameChatCard({
  canOpenChat,
  hasUnread,
  latestChatMessage,
  messageCount = 0,
  onOpenChat,
  senderNames,
}) {
  const body = latestChatMessage?.message_body || 'No messages yet.'
  const senderLabel = getMessageSenderLabel(latestChatMessage, senderNames)

  return (
    <InfoCard
      className={[
        'details-info-card--chat',
        hasUnread ? 'details-info-card--unread' : '',
        !canOpenChat ? 'details-info-card--disabled' : '',
      ].filter(Boolean).join(' ')}
      icon={<ChatIconWithDot active={hasUnread} />}
      title="Game Chat"
      badge={hasUnread && canOpenChat ? 'New' : ''}
      eyebrow=""
      cta="Open chat"
      ctaDisabled={!canOpenChat}
      ctaIcon={<MessageSquare />}
      onCtaClick={onOpenChat}
    >
      <div className="details-chat-card__pills">
        <span className="details-stat-pill">
          <strong>{messageCount}</strong> {messageCount === 1 ? 'message' : 'messages'}
        </span>
      </div>
      <div className="details-chat-preview">
        <span className="details-chat-preview__avatar">{getInitials(senderLabel)}</span>
        <div className="details-chat-preview__body">
          <div className="details-chat-preview__meta">
            <strong>{senderLabel}</strong>
            {latestChatMessage && <small>{formatRelativeTime(latestChatMessage.created_at)}</small>}
          </div>
          <p>{body}</p>
        </div>
      </div>
    </InfoCard>
  )
}

export function ChatPanel({
  currentUserId,
  currentUserName,
  draft,
  error,
  isSending,
  maxLength,
  messages,
  onChangeDraft,
  onClose,
  onSend,
  senderNames,
}) {
  const pinnedMessage = messages.find((message) => message.is_pinned)
  const remainingCharacters = maxLength - draft.length

  return (
    <div className="details-modal-backdrop" role="presentation" onClick={onClose}>
      <section
        className="details-chat-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="details-chat-panel-title"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="details-player-modal__header">
          <div>
            <h2 className="details-chat-title" id="details-chat-panel-title">
              <span>
                <MessageSquare />
              </span>
              Game Chat
            </h2>
          </div>

          <button type="button" aria-label="Close chat" onClick={onClose}>
            ×
          </button>
        </div>

        {pinnedMessage && (
          <div className="details-chat-pinned">
            <strong>Pinned</strong>
            <p>{pinnedMessage.message_body}</p>
          </div>
        )}

        <div className="details-chat-thread">
          {messages.length > 0 ? (
            messages.map((message) => (
              <ChatMessageRow
                currentUserId={currentUserId}
                currentUserName={currentUserName}
                message={message}
                senderNames={senderNames}
                key={message.id}
              />
            ))
          ) : (
            <p className="details-chat-empty">No messages yet.</p>
          )}
        </div>

        <form className="details-chat-composer" onSubmit={onSend}>
          <label htmlFor="details-chat-message">Message</label>
          <textarea
            id="details-chat-message"
            maxLength={maxLength}
            placeholder="Type a message"
            rows={2}
            value={draft}
            onChange={(event) => onChangeDraft(event.target.value)}
          />
          <div className="details-chat-composer__footer">
            <span className={remainingCharacters < 30 ? 'warn' : ''}>
              {draft.length}/{maxLength}
            </span>
            <button type="submit" disabled={isSending || !draft.trim()}>
              {isSending ? 'Sending...' : 'Send'}
            </button>
          </div>
          {error && <p className="details-chat-error">{error}</p>}
        </form>
      </section>
    </div>
  )
}

function ChatIconWithDot({ active }) {
  return (
    <span className="details-chat-icon">
      <MessageSquare />
      {active && <i aria-hidden="true" />}
    </span>
  )
}

function ChatMessageRow({ currentUserId, currentUserName, message, senderNames }) {
  const senderLabel = getMessageSenderLabel(message, senderNames)
  const isSystem = message.message_type === 'system' || message.message_type === 'pinned_update'
  const isOwn = !isSystem && currentUserId && message.sender_user_id === currentUserId
  const avatarLabel = isOwn ? currentUserName || senderLabel : senderLabel

  return (
    <article
      className={[
        'details-chat-message',
        isSystem ? 'details-chat-message--system' : '',
        isOwn ? 'details-chat-message--own' : '',
      ].filter(Boolean).join(' ')}
    >
      <span>{getInitials(avatarLabel)}</span>
      <div>
        <header>
          <strong>{isOwn ? 'You' : senderLabel}</strong>
          <small>{formatRelativeTime(message.created_at)}</small>
        </header>
        <p>{message.message_body}</p>
      </div>
    </article>
  )
}

function getMessageSenderLabel(message, senderNames) {
  if (!message) {
    return 'Pickup Lane'
  }

  if (message.message_type === 'system' || message.message_type === 'pinned_update') {
    return 'Pickup Lane'
  }

  return senderNames.get(message.sender_user_id) || 'Game chat'
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
  return `${hours}h ago`
}
