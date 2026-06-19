import {
  formatAdminDateTime,
  getChatMessageTimelineLabel,
  getChatSenderLabel,
  getPrimaryGameChat,
  getTitleLabel,
} from './adminOfficialGameManageDisplay.js'

function AdminOfficialGameChatTab({
  chatLoadState,
  chatMessages,
  chatRooms,
  error,
  game,
  participants,
  users,
}) {
  const activeChat = getPrimaryGameChat(chatRooms)
  const visibleCount = chatMessages.filter(
    (message) => message.moderation_status === 'visible',
  ).length
  const hiddenCount = chatMessages.filter(
    (message) => message.moderation_status === 'hidden_by_admin',
  ).length
  const flaggedCount = chatMessages.filter(
    (message) => message.moderation_status === 'flagged',
  ).length
  const deletedCount = chatMessages.filter(
    (message) => message.moderation_status === 'deleted_by_sender',
  ).length

  return (
    <section className="admin-official-panel admin-manage-tab-panel" aria-label="Official game chat">
      <div className="admin-manage-panel-heading">
        <div>
          <h2>Chat</h2>
          <p>Read-only room and message inspection for this official game.</p>
        </div>
        <strong>{activeChat ? getTitleLabel(activeChat.chat_status) : 'No room'}</strong>
      </div>

      <div className="admin-bookings-summary" aria-label="Chat summary">
        <div>
          <span>Game setting</span>
          <strong>{game.is_chat_enabled ? 'Enabled' : 'Disabled'}</strong>
        </div>
        <div>
          <span>Room</span>
          <strong>{activeChat ? String(activeChat.id).slice(0, 8) : 'None'}</strong>
        </div>
        <div>
          <span>Loaded messages</span>
          <strong>{chatMessages.length}</strong>
        </div>
        <div>
          <span>Moderation</span>
          <strong>{hiddenCount + flaggedCount + deletedCount}</strong>
        </div>
      </div>

      {activeChat && (
        <div className="admin-chat-room-meta">
          <span>{`Created ${formatAdminDateTime(activeChat.created_at)}`}</span>
          <span>{`Updated ${formatAdminDateTime(activeChat.updated_at)}`}</span>
          <span>
            {activeChat.locked_at
              ? `Locked ${formatAdminDateTime(activeChat.locked_at)}`
              : 'Not locked'}
          </span>
        </div>
      )}

      {error && <p className="admin-official-alert">{error}</p>}
      {chatLoadState === 'loading' && (
        <p className="admin-official-empty">Loading chat.</p>
      )}
      {chatLoadState === 'ready' && !activeChat && (
        <p className="admin-official-empty">No chat room has been created yet.</p>
      )}
      {chatLoadState === 'ready' && activeChat && chatMessages.length === 0 && (
        <p className="admin-official-empty">No messages yet.</p>
      )}

      {chatLoadState === 'ready' && chatMessages.length > 0 && (
        <div className="admin-chat-thread" aria-label="Latest chat messages">
          {chatMessages.map((message) => (
            <article key={message.id} className="admin-chat-message">
              <header>
                <strong>{getChatSenderLabel(message, participants, users)}</strong>
                <span>{formatAdminDateTime(message.created_at)}</span>
                <em>{getTitleLabel(message.moderation_status)}</em>
              </header>
              <p>{message.message_body || 'No message body.'}</p>
              <small>
                {getTitleLabel(message.message_type)} · {getChatMessageTimelineLabel(message)}
              </small>
            </article>
          ))}
        </div>
      )}

      {chatMessages.length > 0 && (
        <p className="admin-chat-footnote">
          Showing latest loaded messages: {visibleCount} visible, {flaggedCount} flagged,
          {' '}
          {hiddenCount} hidden,
          {' '}
          {deletedCount} sender-deleted.
        </p>
      )}
    </section>
  )
}

export default AdminOfficialGameChatTab
