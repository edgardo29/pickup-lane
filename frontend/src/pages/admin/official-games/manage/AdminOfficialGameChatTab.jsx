import { ChatIcon } from '../../../../components/BrowseIcons.jsx'
import AdminOfficialGameEmptyState from './AdminOfficialGameEmptyState.jsx'
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
    <section className="admin-manage-tab-panel admin-bookings-panel" aria-label="Official game chat">
      <div className="admin-manage-panel-heading admin-bookings-heading">
        <div className="admin-bookings-heading__copy">
          <span className="admin-bookings-heading__icon">
            <ChatIcon />
          </span>
          <div>
            <h2>Chat</h2>
            <p>Inspect room status and moderation activity.</p>
          </div>
        </div>
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
        <AdminOfficialGameEmptyState icon={ChatIcon} title="No chat room yet">
          A room will appear here when chat is created for this game.
        </AdminOfficialGameEmptyState>
      )}
      {chatLoadState === 'ready' && activeChat && chatMessages.length === 0 && (
        <AdminOfficialGameEmptyState icon={ChatIcon} title="No messages yet">
          New messages will appear here once players start chatting.
        </AdminOfficialGameEmptyState>
      )}

      {chatLoadState === 'ready' && chatMessages.length > 0 && (
        <div className="admin-chat-thread" aria-label="Latest chat messages">
          {chatMessages.map((message) => (
            <article key={message.id} className="admin-chat-message">
              <header>
                <strong>{getChatSenderLabel(message, participants)}</strong>
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
