import { useEffect, useState } from 'react'
import { EyeOff, Trash2 } from 'lucide-react'
import { FormErrorMessage } from '../../../components/FormErrorMessage.jsx'
import { moderateAdminNeedASubChatMessage } from '../shared/adminApi.js'

function createIdempotencyKey(action, messageId) {
  const randomPart = globalThis.crypto?.randomUUID?.()
    ?? `${Date.now()}-${Math.random().toString(16).slice(2)}`
  return `admin-sub-chat-${action}-${messageId}-${randomPart}`
}

function AdminNeedASubChatModerationModal({
  action,
  firebaseUser,
  message,
  onClose,
  onModerated,
  postId,
}) {
  const isRemove = action === 'remove'
  const [reason, setReason] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [executionError, setExecutionError] = useState('')
  const [idempotencyKey] = useState(
    () => createIdempotencyKey(action, message.id),
  )

  useEffect(() => {
    const originalOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    function handleKeyDown(event) {
      if (event.key === 'Escape' && !isSubmitting) {
        onClose()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => {
      document.body.style.overflow = originalOverflow
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [isSubmitting, onClose])

  async function handleSubmit(event) {
    event.preventDefault()
    if (!reason.trim() || isSubmitting) return

    setIsSubmitting(true)
    setExecutionError('')
    try {
      const result = await moderateAdminNeedASubChatMessage({
        action,
        firebaseUser,
        idempotencyKey,
        messageId: message.id,
        postId,
        reason: reason.trim(),
      })
      onModerated(result)
      onClose()
    } catch (error) {
      setExecutionError(error.message || 'Chat message could not be moderated.')
    } finally {
      setIsSubmitting(false)
    }
  }

  function handleBackdropClick() {
    if (!isSubmitting) onClose()
  }

  const Icon = isRemove ? Trash2 : EyeOff
  const title = isRemove ? 'Remove message?' : 'Hide message?'

  return (
    <div
      className="admin-sub-modal-backdrop"
      role="presentation"
      onClick={handleBackdropClick}
    >
      <section
        aria-labelledby="admin-sub-chat-moderation-title"
        aria-modal="true"
        className="admin-sub-modal"
        role="dialog"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="admin-sub-modal__header">
          <span><Icon /></span>
          <div>
            <h2 id="admin-sub-chat-moderation-title">{title}</h2>
            <p>{message.sender_display_name_snapshot}</p>
          </div>
        </header>
        <form className="admin-sub-modal__form" onSubmit={handleSubmit}>
          <p>
            {isRemove
              ? 'Removes this message from member chat while retaining its support record.'
              : 'Hides this message from members while retaining it for support review.'}
          </p>
          <div className="admin-sub-chat-modal-message">
            {message.message_body}
          </div>
          <label>
            <span>Internal reason</span>
            <textarea
              disabled={isSubmitting}
              maxLength={1000}
              placeholder="Required moderation reason"
              value={reason}
              onChange={(event) => setReason(event.target.value)}
            />
            <small>{reason.length}/1000</small>
          </label>
          {executionError && (
            <div className="admin-sub-modal__message">
              <FormErrorMessage>{executionError}</FormErrorMessage>
            </div>
          )}
          <div className="admin-sub-modal__actions">
            <button
              className="admin-sub-modal__secondary"
              disabled={isSubmitting}
              type="button"
              onClick={onClose}
            >
              Back
            </button>
            <button
              className="admin-sub-modal__danger"
              disabled={isSubmitting || !reason.trim()}
              type="submit"
            >
              {isSubmitting
                ? isRemove ? 'Removing' : 'Hiding'
                : isRemove ? 'Remove message' : 'Hide message'}
            </button>
          </div>
        </form>
      </section>
    </div>
  )
}

export default AdminNeedASubChatModerationModal
