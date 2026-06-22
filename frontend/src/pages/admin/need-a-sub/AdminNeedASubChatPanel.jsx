import { useEffect, useState } from 'react'
import {
  ChevronLeft,
  ChevronRight,
  EyeOff,
  MessageSquareText,
  RefreshCw,
  Trash2,
} from 'lucide-react'
import { SkeletonBlock } from '../../../components/skeleton/index.js'
import { getAdminNeedASubChat } from '../shared/adminApi.js'
import {
  formatAdminNeedASubDateTime,
  formatAdminNeedASubStatus,
  shortAdminNeedASubId,
} from './adminNeedASubFormatters.js'
import AdminNeedASubChatModerationModal from './AdminNeedASubChatModerationModal.jsx'

const CHAT_PAGE_SIZE = 50

function AdminNeedASubChatPanel({
  firebaseUser,
  onModerated,
  postId,
  timeZone,
}) {
  const [chat, setChat] = useState(null)
  const [loadState, setLoadState] = useState('loading')
  const [loadError, setLoadError] = useState('')
  const [refreshCount, setRefreshCount] = useState(0)
  const [moderationTarget, setModerationTarget] = useState(null)
  const [offset, setOffset] = useState(0)

  useEffect(() => {
    let isMounted = true

    async function loadChat() {
      if (!firebaseUser || !postId) return
      setLoadState('loading')
      setLoadError('')
      try {
        const response = await getAdminNeedASubChat({
          firebaseUser,
          limit: CHAT_PAGE_SIZE,
          offset,
          postId,
        })
        if (!isMounted) return
        if (
          offset > 0
          && response.total_message_count > 0
          && response.messages.length === 0
        ) {
          const lastPageOffset = Math.floor(
            (response.total_message_count - 1) / CHAT_PAGE_SIZE,
          ) * CHAT_PAGE_SIZE
          setOffset(lastPageOffset)
          return
        }
        setChat(response)
        setLoadState('ready')
      } catch (error) {
        if (!isMounted) return
        setChat(null)
        setLoadError(error.message || 'Need a Sub chat could not be loaded.')
        setLoadState('error')
      }
    }

    loadChat()
    return () => {
      isMounted = false
    }
  }, [firebaseUser, offset, postId, refreshCount])

  function handleModerated(result) {
    setChat((current) => {
      if (!current) return current
      return {
        ...current,
        messages: current.messages.map((message) => (
          message.id === result.message.id ? result.message : message
        )),
      }
    })
    onModerated()
  }

  return (
    <section className="admin-sub-detail-panel">
      <div className="admin-sub-detail-panel__heading">
        <div>
          <MessageSquareText />
          <h2>Scoped Chat</h2>
        </div>
        <div className="admin-sub-chat-heading-actions">
          <span>{chat?.total_message_count ?? 0} messages</span>
          <button
            aria-label="Refresh Need a Sub chat"
            className="admin-sub-button admin-sub-button--icon"
            type="button"
            onClick={() => setRefreshCount((count) => count + 1)}
          >
            <RefreshCw />
          </button>
        </div>
      </div>

      {loadState === 'loading' && (
        <div className="admin-sub-chat-loading" role="status">
          <SkeletonBlock height="4rem" rounded width="100%" />
          <SkeletonBlock height="4rem" rounded width="100%" />
        </div>
      )}
      {loadError && <p className="admin-sub-alert">{loadError}</p>}
      {loadState === 'ready' && chat?.chat_status === 'not_created' && (
        <p className="admin-sub-empty-line">No scoped chat has been created.</p>
      )}
      {loadState === 'ready' && chat?.chat_status !== 'not_created' && (
        <>
          <div className="admin-sub-chat-summary">
            <span>{formatAdminNeedASubStatus(chat.chat_status)}</span>
            <span>
              Created {formatAdminNeedASubDateTime(chat.created_at, timeZone)}
            </span>
            <code>{shortAdminNeedASubId(chat.chat_id)}</code>
          </div>
          {!chat.messages.length ? (
            <p className="admin-sub-empty-line">No chat messages found.</p>
          ) : (
            <div className="admin-sub-chat-list">
              {chat.messages.map((message) => {
                const canHide = ['visible', 'flagged'].includes(
                  message.moderation_status,
                )
                const canRemove = ![
                  'removed_by_admin',
                  'deleted_by_sender',
                ].includes(message.moderation_status)

                return (
                  <article key={message.id}>
                    <header>
                      <div>
                        <strong>{message.sender_display_name_snapshot}</strong>
                        <span>
                          {formatAdminNeedASubDateTime(
                            message.created_at,
                            timeZone,
                          )}
                        </span>
                      </div>
                      <span className={`admin-sub-status admin-sub-status--${message.moderation_status}`}>
                        {formatAdminNeedASubStatus(message.moderation_status)}
                      </span>
                    </header>
                    <p>{message.message_body}</p>
                    <footer>
                      <code>{shortAdminNeedASubId(message.id)}</code>
                      <div>
                        {canHide && (
                          <button
                            className="admin-sub-button"
                            type="button"
                            onClick={() => setModerationTarget({
                              action: 'hide',
                              message,
                            })}
                          >
                            <EyeOff />
                            Hide
                          </button>
                        )}
                        {canRemove && (
                          <button
                            className="admin-sub-button admin-sub-button--danger"
                            type="button"
                            onClick={() => setModerationTarget({
                              action: 'remove',
                              message,
                            })}
                          >
                            <Trash2 />
                            Remove
                          </button>
                        )}
                      </div>
                    </footer>
                  </article>
                )
              })}
            </div>
          )}
          {chat.total_message_count > chat.limit && (
            <nav
              aria-label="Scoped chat pagination"
              className="admin-sub-pagination"
            >
              <span>
                {chat.total_message_count
                  ? chat.offset + 1
                  : 0}
                -
                {Math.min(
                  chat.offset + chat.messages.length,
                  chat.total_message_count,
                )} of {chat.total_message_count}
              </span>
              <div>
                <button
                  aria-label="Previous scoped chat page"
                  className="admin-sub-button admin-sub-button--icon"
                  disabled={chat.offset <= 0}
                  title="Previous page"
                  type="button"
                  onClick={() => setOffset(Math.max(0, chat.offset - chat.limit))}
                >
                  <ChevronLeft />
                </button>
                <button
                  aria-label="Next scoped chat page"
                  className="admin-sub-button admin-sub-button--icon"
                  disabled={
                    chat.offset + chat.messages.length
                    >= chat.total_message_count
                  }
                  title="Next page"
                  type="button"
                  onClick={() => setOffset(chat.offset + chat.limit)}
                >
                  <ChevronRight />
                </button>
              </div>
            </nav>
          )}
        </>
      )}

      {moderationTarget && (
        <AdminNeedASubChatModerationModal
          action={moderationTarget.action}
          firebaseUser={firebaseUser}
          message={moderationTarget.message}
          postId={postId}
          onClose={() => setModerationTarget(null)}
          onModerated={handleModerated}
        />
      )}
    </section>
  )
}

export default AdminNeedASubChatPanel
