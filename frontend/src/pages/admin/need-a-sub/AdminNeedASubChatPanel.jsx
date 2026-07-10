import { useCallback, useEffect, useState } from 'react'
import { MessageSquareText } from 'lucide-react'
import { SkeletonBlock } from '../../../components/skeleton/index.js'
import AdminChatModerationPanel from '../shared/AdminChatModerationPanel.jsx'
import {
  getAdminNeedASubChatSummary,
  listAdminNeedASubChatModerationMessages,
  moderateAdminNeedASubChatMessage,
} from '../shared/adminApi.js'
import {
  formatAdminNeedASubDateTime,
  formatAdminNeedASubStatus,
} from './adminNeedASubFormatters.js'

function AdminNeedASubChatPanel({
  firebaseUser,
  postId,
  timeZone,
}) {
  const [summary, setSummary] = useState(null)
  const [loadState, setLoadState] = useState('loading')
  const [loadError, setLoadError] = useState('')
  const [refreshCount, setRefreshCount] = useState(0)

  const loadChatMessages = useCallback((options) => (
    listAdminNeedASubChatModerationMessages({
      ...options,
      postId,
    })
  ), [postId])

  const moderateChatMessage = useCallback((options) => (
    moderateAdminNeedASubChatMessage({
      ...options,
      postId,
    })
  ), [postId])

  const refreshChatSummary = useCallback(() => {
    setRefreshCount((count) => count + 1)
  }, [])

  const formatChatDateTime = useCallback((value) => (
    formatAdminNeedASubDateTime(value, timeZone)
  ), [timeZone])

  useEffect(() => {
    let isMounted = true

    async function loadSummary() {
      if (!firebaseUser || !postId) return
      setLoadState('loading')
      setLoadError('')
      try {
        const response = await getAdminNeedASubChatSummary({
          firebaseUser,
          postId,
        })
        if (!isMounted) return
        setSummary(response)
        setLoadState('ready')
      } catch (error) {
        if (!isMounted) return
        setSummary(null)
        setLoadError(error.message || 'Need a Sub chat summary could not be loaded.')
        setLoadState('error')
      }
    }

    loadSummary()
    return () => {
      isMounted = false
    }
  }, [firebaseUser, postId, refreshCount])

  return (
    <section className="admin-sub-section admin-sub-chat-panel">
      <div className="admin-sub-section__heading">
        <div>
          <MessageSquareText />
          <h2>Post Chat</h2>
        </div>
      </div>

      {loadState === 'loading' && (
        <div className="admin-sub-chat-loading" role="status">
          <SkeletonBlock height="4rem" rounded width="100%" />
        </div>
      )}
      {loadError && <p className="admin-sub-alert">{loadError}</p>}
      {loadState === 'ready' && summary && (
        <>
          <div className="admin-sub-chat-summary-grid">
            <div>
              <span>Status</span>
              <strong>{formatAdminNeedASubStatus(summary.chat_status)}</strong>
            </div>
            <div>
              <span>Visible</span>
              <strong>{summary.message_count}</strong>
            </div>
            <div>
              <span>Needs review</span>
              <strong>{summary.needs_review_count}</strong>
            </div>
            <div>
              <span>Removed</span>
              <strong>{summary.removed_count}</strong>
            </div>
          </div>

          <AdminChatModerationPanel
            firebaseUser={firebaseUser}
            formatDateTime={formatChatDateTime}
            loadMessages={loadChatMessages}
            moderateMessage={moderateChatMessage}
            needsReviewCount={summary.needs_review_count}
            onAfterAction={refreshChatSummary}
            refreshToken={refreshCount}
            removedMessageCount={summary.removed_count}
            visibleMessageCount={summary.message_count}
          />
        </>
      )}
    </section>
  )
}

export default AdminNeedASubChatPanel
