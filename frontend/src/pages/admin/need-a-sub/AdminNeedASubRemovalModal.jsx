import { useEffect, useState } from 'react'
import { Trash2 } from 'lucide-react'
import { FormErrorMessage } from '../../../components/FormErrorMessage.jsx'
import { removeAdminNeedASubPost } from '../shared/adminApi.js'
import { formatAdminNeedASubStatus } from './adminNeedASubFormatters.js'

function createRemovalIdempotencyKey(postId) {
  const suffix = globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random()}`
  return `admin-need-a-sub-remove:${postId}:${suffix}`
}

function AdminNeedASubRemovalModal({
  detail,
  firebaseUser,
  onClose,
  onRemoved,
}) {
  const [reason, setReason] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [executionError, setExecutionError] = useState('')
  const [idempotencyKey, setIdempotencyKey] = useState(
    () => createRemovalIdempotencyKey(detail.post.id),
  )
  const activeRequestCount = (
    detail.request_counts.pending_count
    + detail.request_counts.confirmed_count
    + detail.request_counts.waitlisted_count
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
    if (!reason.trim() || isSubmitting) {
      return
    }

    setIsSubmitting(true)
    setExecutionError('')

    try {
      const result = await removeAdminNeedASubPost({
        firebaseUser,
        idempotencyKey,
        postId: detail.post.id,
        reason: reason.trim(),
      })
      onRemoved(result)
      onClose()
    } catch (error) {
      setExecutionError(error.message || 'Need a Sub post could not be removed.')
    } finally {
      setIsSubmitting(false)
    }
  }

  function handleReasonChange(event) {
    setReason(event.target.value)
    setIdempotencyKey(createRemovalIdempotencyKey(detail.post.id))
  }

  function handleBackdropClick() {
    if (!isSubmitting) {
      onClose()
    }
  }

  return (
    <div
      className="admin-sub-modal-backdrop"
      role="presentation"
      onClick={handleBackdropClick}
    >
      <section
        aria-labelledby="admin-sub-remove-title"
        aria-modal="true"
        className="admin-sub-modal"
        role="dialog"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="admin-sub-modal__header">
          <span><Trash2 /></span>
          <div>
            <h2 id="admin-sub-remove-title">Remove post?</h2>
            <p>{detail.post.team_name || 'Need a Sub post'}</p>
          </div>
        </header>

        <form className="admin-sub-modal__form" onSubmit={handleSubmit}>
          <p>
            The post will leave normal user views. Its owner and affected
            requesters will receive a Pickup Lane removal notice.
          </p>
          <div className="admin-sub-modal__facts">
            <div>
              <span>Current status</span>
              <strong>{formatAdminNeedASubStatus(detail.post.post_status)}</strong>
            </div>
            <div>
              <span>Active requests closed</span>
              <strong>{activeRequestCount}</strong>
            </div>
          </div>
          <label>
            <span>Internal reason</span>
            <textarea
              disabled={isSubmitting}
              maxLength={500}
              placeholder="Required removal reason"
              value={reason}
              onChange={handleReasonChange}
            />
            <small>{reason.length}/500</small>
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
              {isSubmitting ? 'Removing' : 'Remove post'}
            </button>
          </div>
        </form>
      </section>
    </div>
  )
}

export default AdminNeedASubRemovalModal
