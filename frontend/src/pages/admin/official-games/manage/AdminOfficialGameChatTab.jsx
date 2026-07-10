import { useCallback } from 'react'
import { RefreshCw } from 'lucide-react'
import { ChatIcon } from '../../../../components/BrowseIcons.jsx'
import AdminChatModerationPanel from '../../shared/AdminChatModerationPanel.jsx'
import {
  listAdminOfficialGameChatModerationMessages,
  moderateAdminOfficialGameChatMessage,
} from '../../shared/adminApi.js'
import AdminOfficialGameEmptyState from './AdminOfficialGameEmptyState.jsx'
import {
  formatAdminDateTime,
  getTitleLabel,
} from './adminOfficialGameManageDisplay.js'

function AdminOfficialGameChatTab({
  chatLoadState,
  chatSummary,
  error,
  firebaseUser,
  game,
  onRetry,
  refreshToken = 0,
}) {
  const loadChatMessages = useCallback((options) => (
    listAdminOfficialGameChatModerationMessages({
      ...options,
      gameId: game.id,
    })
  ), [game.id])

  const moderateChatMessage = useCallback((options) => (
    moderateAdminOfficialGameChatMessage({
      ...options,
      gameId: game.id,
    })
  ), [game.id])

  return (
    <section className="admin-manage-tab-panel admin-bookings-panel" aria-label="Official game chat">
      <div className="admin-manage-panel-heading admin-bookings-heading admin-chat-heading">
        <div className="admin-bookings-heading__copy">
          <span className="admin-bookings-heading__icon">
            <ChatIcon />
          </span>
          <div>
            <h2>Chat</h2>
            <p>Review game chat status and moderation counts.</p>
          </div>
        </div>
        <button
          className="admin-official-icon-button"
          type="button"
          onClick={onRetry}
          aria-label="Refresh chat summary"
        >
          <RefreshCw />
        </button>
      </div>

      {error && <p className="admin-official-alert">{error}</p>}
      {chatLoadState === 'loading' && (
        <p className="admin-official-empty">Loading chat summary.</p>
      )}
      {chatLoadState === 'ready' && !chatSummary && (
        <AdminOfficialGameEmptyState icon={ChatIcon} title="No chat data">
          Chat summary could not be loaded for this game.
        </AdminOfficialGameEmptyState>
      )}
      {chatLoadState === 'ready' && chatSummary && (
        <>
          <div className="admin-bookings-summary" aria-label="Chat summary">
            <div>
              <span>Game setting</span>
              <strong>{game.is_chat_enabled ? 'Enabled' : 'Disabled'}</strong>
            </div>
            <div>
              <span>Room</span>
              <strong>{getTitleLabel(chatSummary.chat_status)}</strong>
            </div>
            <div>
              <span>Visible</span>
              <strong>{chatSummary.message_count}</strong>
            </div>
            <div>
              <span>Needs review</span>
              <strong>{chatSummary.needs_review_count}</strong>
            </div>
            <div>
              <span>Removed</span>
              <strong>{chatSummary.removed_count}</strong>
            </div>
          </div>

          <AdminChatModerationPanel
            firebaseUser={firebaseUser}
            formatDateTime={formatAdminDateTime}
            loadMessages={loadChatMessages}
            moderateMessage={moderateChatMessage}
            needsReviewCount={chatSummary.needs_review_count}
            onAfterAction={onRetry}
            refreshToken={refreshToken}
            removedMessageCount={chatSummary.removed_count}
            visibleMessageCount={chatSummary.message_count}
          />
        </>
      )}
    </section>
  )
}

export default AdminOfficialGameChatTab
