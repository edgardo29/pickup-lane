import { useEffect, useState } from 'react'
import {
  AlertCircle,
  Check,
  ChevronLeft,
  ChevronRight,
  Eye,
  MessageSquareText,
  RotateCcw,
  Trash2,
  X,
} from 'lucide-react'
import '../../../styles/admin/AdminChatModerationPanel.css'

const PAGE_SIZE = 20
const LIST_BADGE_LIMIT = 2

const VIEW_OPTIONS = [
  { value: 'all', label: 'All messages' },
  { value: 'needs_review', label: 'Needs review' },
  { value: 'removed', label: 'Removed' },
]

function formatStatus(value) {
  return String(value || '')
    .split('_')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ') || 'Unknown'
}

function makeIdempotencyKey(action, messageId) {
  const randomId = globalThis.crypto?.randomUUID?.()
  return randomId
    ? `${action}-${randomId}`
    : `${action}-${messageId}-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

function getKnownCountForView({
  needsReviewCount,
  removedMessageCount,
  view,
  visibleMessageCount,
}) {
  if (view === 'needs_review') return needsReviewCount
  if (view === 'removed') return removedMessageCount
  return visibleMessageCount + removedMessageCount
}

function getEmptyState(view, fallback) {
  if (view === 'needs_review') {
    return {
      title: 'No messages need review',
      body: 'Messages flagged for moderation will appear here.',
    }
  }

  if (view === 'removed') {
    return {
      title: 'No removed messages',
      body: 'Removed chat messages will appear here.',
    }
  }

  return {
    title: 'No chat messages yet',
    body: fallback,
  }
}

function getMessageBadges(message) {
  const badges = []

  if (message.review_status === 'needs_review') {
    badges.push({
      label: 'Needs review',
      tone: 'warning',
    })
  }

  if (message.visibility_status === 'removed') {
    badges.push({
      label: 'Removed',
      tone: 'danger',
    })
  }

  message.detections?.forEach((detection) => {
    badges.push({
      label: `${formatStatus(detection.category)}: ${formatStatus(detection.severity)}`,
      tone: 'neutral',
    })
  })

  return badges
}

function getIssueText(badges, limit = LIST_BADGE_LIMIT) {
  if (!badges.length) return ''

  const hiddenBadgeCount = Math.max(0, badges.length - limit)
  const labels = badges.slice(0, limit).map((badge) => badge.label)

  if (hiddenBadgeCount > 0) {
    labels.push(`+${hiddenBadgeCount}`)
  }

  return labels.join(' · ')
}

function getIssueTone(badges) {
  if (badges.some((badge) => badge.tone === 'danger')) return 'danger'
  if (badges.some((badge) => badge.tone === 'warning')) return 'warning'
  return 'neutral'
}

function getDetectionLabels(message) {
  return (message.detections || []).map((detection) => (
    `${formatStatus(detection.category)}: ${formatStatus(detection.severity)}`
  ))
}

function AdminChatModerationPanel({
  emptyMessage = 'No chat messages found.',
  firebaseUser,
  formatDateTime,
  loadMessages,
  moderateMessage,
  needsReviewCount = 0,
  onAfterAction,
  refreshToken = 0,
  removedMessageCount = 0,
  visibleMessageCount = 0,
}) {
  const [view, setView] = useState('all')
  const [offset, setOffset] = useState(0)
  const [messages, setMessages] = useState([])
  const [totalCount, setTotalCount] = useState(0)
  const [loadState, setLoadState] = useState('idle')
  const [loadError, setLoadError] = useState('')
  const [activeAction, setActiveAction] = useState(null)
  const [selectedMessage, setSelectedMessage] = useState(null)

  const pageStart = messages.length ? offset + 1 : 0
  const pageEnd = messages.length ? Math.min(offset + messages.length, totalCount) : 0
  const hasPrevious = offset > 0
  const hasNext = offset + messages.length < totalCount
  const knownCountForView = getKnownCountForView({
    needsReviewCount,
    removedMessageCount,
    view,
    visibleMessageCount,
  })
  const hasMessagesForView = loadState === 'ready' && knownCountForView > 0 && messages.length > 0
  const showPagination = hasMessagesForView && (totalCount > PAGE_SIZE || offset > 0)
  const emptyState = getEmptyState(view, emptyMessage)

  useEffect(() => {
    let isMounted = true

    async function loadPage() {
      if (!firebaseUser) {
        setMessages([])
        setTotalCount(0)
        setLoadState('idle')
        setLoadError('')
        return
      }

      if (knownCountForView <= 0) {
        setMessages([])
        setTotalCount(0)
        setLoadState('ready')
        setLoadError('')
        return
      }

      setMessages([])
      setTotalCount(0)
      setLoadState('loading')
      setLoadError('')

      try {
        const response = await loadMessages({
          firebaseUser,
          limit: PAGE_SIZE,
          offset,
          view,
        })
        if (!isMounted) return
        setMessages(response.messages || [])
        setTotalCount(response.total_count || 0)
        setLoadState('ready')
      } catch (error) {
        if (!isMounted) return
        setMessages([])
        setTotalCount(0)
        setLoadError(error.message || 'Chat messages could not be loaded.')
        setLoadState('error')
      }
    }

    loadPage()

    return () => {
      isMounted = false
    }
  }, [firebaseUser, knownCountForView, loadMessages, offset, refreshToken, view])

  function selectView(nextView) {
    const nextKnownCount = getKnownCountForView({
      needsReviewCount,
      removedMessageCount,
      view: nextView,
      visibleMessageCount,
    })
    setView(nextView)
    setOffset(0)
    setMessages([])
    setTotalCount(0)
    setLoadError('')
    setLoadState(nextKnownCount > 0 ? 'loading' : 'ready')
    setActiveAction(null)
    setSelectedMessage(null)
  }

  function openMessageDetail(message, rowNumber, action = '') {
    setSelectedMessage({
      message,
      rowNumber,
    })

    if (action === 'remove' || action === 'restore') {
      setActiveAction({
        action,
        error: '',
        messageId: message.id,
        reason: '',
      })
      return
    }

    setActiveAction(null)
  }

  function closeMessageDetail() {
    if (activeAction?.submitting) return
    setSelectedMessage(null)
    setActiveAction(null)
  }

  function goToOffset(nextOffset) {
    setSelectedMessage(null)
    setActiveAction(null)
    setOffset(nextOffset)
  }

  async function submitAction(message, action, reason = '') {
    const trimmedReason = reason.trim()
    const needsReason = action === 'remove' || action === 'restore'

    if (needsReason && !trimmedReason) {
      setActiveAction({
        action,
        error: 'Reason is required.',
        messageId: message.id,
        reason,
      })
      return
    }

    setActiveAction({
      action,
      error: '',
      messageId: message.id,
      reason,
      submitting: true,
    })

    try {
      await moderateMessage({
        action,
        firebaseUser,
        idempotencyKey: makeIdempotencyKey(action, message.id),
        messageId: message.id,
        ...(needsReason ? { reason: trimmedReason } : {}),
      })
      setActiveAction(null)
      if (selectedMessage?.message.id === message.id) {
        setSelectedMessage(null)
      }
      onAfterAction?.()
    } catch (error) {
      setActiveAction({
        action,
        error: error.message || 'Chat moderation action failed.',
        messageId: message.id,
        reason,
      })
    }
  }

  if (!firebaseUser) {
    return null
  }

  const detailMessage = selectedMessage?.message
  const detailDraft = (
    detailMessage && activeAction?.messageId === detailMessage.id
      ? activeAction
      : null
  )
  const detailNeedsReview = detailMessage?.review_status === 'needs_review'
  const detailIsRemoved = detailMessage?.visibility_status === 'removed'
  const detailFlagText = detailMessage
    ? getDetectionLabels(detailMessage).join(' · ') || 'None'
    : ''

  return (
    <section className="admin-chat-moderation" aria-label="Chat message moderation">
      <div className="admin-chat-moderation__toolbar">
        <div className="admin-chat-moderation__tabs" role="tablist" aria-label="Message filters">
          {VIEW_OPTIONS.map((option) => (
            <button
              aria-selected={view === option.value}
              className={view === option.value ? 'is-active' : ''}
              key={option.value}
              role="tab"
              type="button"
              onClick={() => selectView(option.value)}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      {loadState === 'loading' && (
        <p className="admin-chat-moderation__empty" role="status">
          Loading chat messages.
        </p>
      )}

      {loadError && <p className="admin-chat-moderation__error">{loadError}</p>}

      {loadState === 'ready' && !hasMessagesForView && (
        <div className="admin-chat-moderation__empty-state">
          <span className="admin-chat-moderation__empty-icon">
            <MessageSquareText />
          </span>
          <div>
            <strong>{emptyState.title}</strong>
            <p>{emptyState.body}</p>
          </div>
        </div>
      )}

      {hasMessagesForView && (
        <div className="admin-chat-moderation__list">
          {messages.map((message, index) => {
            const badges = getMessageBadges(message)
            const issueText = getIssueText(badges)
            const issueTone = getIssueTone(badges)
            const rowNumber = offset + index + 1
            return (
              <article className="admin-chat-moderation__message" key={message.id}>
                <header className="admin-chat-moderation__message-header">
                  <div>
                    <strong>{message.sender_display_name}</strong>
                  </div>
                  <span className="admin-chat-moderation__message-meta">
                    <span>#{rowNumber}</span>
                    <span aria-hidden="true">·</span>
                    <time dateTime={message.created_at}>
                      {formatDateTime(message.created_at)}
                    </time>
                  </span>
                </header>

                <div className="admin-chat-moderation__message-content">
                  <p className="admin-chat-moderation__body">{message.message_body}</p>
                </div>

                <footer className="admin-chat-moderation__message-footer">
                  <div className="admin-chat-moderation__issue-slot">
                    {issueText && (
                      <p
                        className={`admin-chat-moderation__issue-text admin-chat-moderation__issue-text--${issueTone}`}
                      >
                        <AlertCircle />
                        <span>{issueText}</span>
                      </p>
                    )}
                  </div>
                  <button
                    className="admin-chat-moderation__button admin-chat-moderation__button--list"
                    type="button"
                    onClick={() => openMessageDetail(message, rowNumber)}
                  >
                    <Eye />
                    View
                  </button>
                </footer>
              </article>
            )
          })}
        </div>
      )}

      {showPagination && (
        <div className="admin-chat-moderation__pagination">
          <span>{pageStart}-{pageEnd} of {totalCount}</span>
          <div>
            <button
              aria-label="Previous chat messages"
              className="admin-chat-moderation__button admin-chat-moderation__button--icon"
              disabled={!hasPrevious}
              type="button"
              onClick={() => goToOffset(Math.max(0, offset - PAGE_SIZE))}
            >
              <ChevronLeft />
            </button>
            <button
              aria-label="Next chat messages"
              className="admin-chat-moderation__button admin-chat-moderation__button--icon"
              disabled={!hasNext}
              type="button"
              onClick={() => goToOffset(offset + PAGE_SIZE)}
            >
              <ChevronRight />
            </button>
          </div>
        </div>
      )}

      {detailMessage && (
        <div
          className="admin-chat-moderation__modal-backdrop"
          role="presentation"
          onClick={closeMessageDetail}
        >
          <section
            aria-labelledby="admin-chat-message-detail-title"
            aria-modal="true"
            className="admin-chat-moderation__modal"
            role="dialog"
            onClick={(event) => event.stopPropagation()}
          >
            <header className="admin-chat-moderation__modal-header">
              <div>
                <span className="admin-chat-moderation__modal-icon">
                  <MessageSquareText />
                </span>
                <h2 id="admin-chat-message-detail-title">Message Details</h2>
              </div>
              <button
                aria-label="Close chat message detail"
                className="admin-chat-moderation__button admin-chat-moderation__button--icon"
                disabled={detailDraft?.submitting}
                type="button"
                onClick={closeMessageDetail}
              >
                <X />
              </button>
            </header>

            <section className="admin-chat-moderation__modal-subject">
              <h3>{detailMessage.sender_display_name}</h3>
              <p>
                #{selectedMessage.rowNumber} · {formatDateTime(detailMessage.created_at)}
              </p>
            </section>

            <div className="admin-chat-moderation__modal-fields">
              <div className="admin-chat-moderation__modal-field-group">
                <span>Visibility</span>
                <div className="admin-chat-moderation__modal-field">
                  <strong>{formatStatus(detailMessage.visibility_status)}</strong>
                </div>
              </div>
              <div className="admin-chat-moderation__modal-field-group">
                <span>Review Status</span>
                <div className="admin-chat-moderation__modal-field">
                  <strong>{formatStatus(detailMessage.review_status)}</strong>
                </div>
              </div>
              <div className="admin-chat-moderation__modal-field-group admin-chat-moderation__modal-field-group--wide">
                <span>Flags</span>
                <div className="admin-chat-moderation__modal-field">
                  <strong>{detailFlagText}</strong>
                </div>
              </div>
              <section className="admin-chat-moderation__modal-field-group admin-chat-moderation__modal-field-group--wide">
                <span>Message</span>
                <div className="admin-chat-moderation__modal-field admin-chat-moderation__modal-field--message">
                  <p>{detailMessage.message_body}</p>
                </div>
              </section>
            </div>

            <div className="admin-chat-moderation__modal-actions">
              {detailNeedsReview && (
                <button
                  className="admin-chat-moderation__button"
                  disabled={detailDraft?.submitting}
                  type="button"
                  onClick={() => submitAction(detailMessage, 'review')}
                >
                  <Check />
                  Mark reviewed
                </button>
              )}
              {!detailIsRemoved && (
                <button
                  className="admin-chat-moderation__button admin-chat-moderation__button--danger"
                  disabled={detailDraft?.submitting}
                  type="button"
                  onClick={() => setActiveAction({
                    action: 'remove',
                    error: '',
                    messageId: detailMessage.id,
                    reason: '',
                  })}
                >
                  <Trash2 />
                  Remove
                </button>
              )}
              {detailIsRemoved && (
                <button
                  className="admin-chat-moderation__button"
                  disabled={detailDraft?.submitting}
                  type="button"
                  onClick={() => setActiveAction({
                    action: 'restore',
                    error: '',
                    messageId: detailMessage.id,
                    reason: '',
                  })}
                >
                  <RotateCcw />
                  Restore
                </button>
              )}
            </div>

            {(detailDraft?.action === 'remove' || detailDraft?.action === 'restore') && (
              <form
                className="admin-chat-moderation__action-form admin-chat-moderation__modal-form"
                onSubmit={(event) => {
                  event.preventDefault()
                  submitAction(detailMessage, detailDraft.action, detailDraft.reason)
                }}
              >
                <label htmlFor={`chat-moderation-reason-${detailMessage.id}`}>
                  Reason
                </label>
                <textarea
                  id={`chat-moderation-reason-${detailMessage.id}`}
                  rows={4}
                  value={detailDraft.reason}
                  onChange={(event) => setActiveAction({
                    ...detailDraft,
                    error: '',
                    reason: event.target.value,
                  })}
                />
                {detailDraft.error && (
                  <p className="admin-chat-moderation__error">{detailDraft.error}</p>
                )}
                <div>
                  <button
                    className="admin-chat-moderation__button"
                    disabled={detailDraft.submitting}
                    type="button"
                    onClick={() => setActiveAction(null)}
                  >
                    Cancel
                  </button>
                  <button
                    className="admin-chat-moderation__button admin-chat-moderation__button--primary"
                    disabled={detailDraft.submitting}
                    type="submit"
                  >
                    {detailDraft.submitting ? 'Saving' : 'Confirm'}
                  </button>
                </div>
              </form>
            )}
          </section>
        </div>
      )}
    </section>
  )
}

export default AdminChatModerationPanel
