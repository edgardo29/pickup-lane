import { useEffect, useState } from 'react'
import { Eye, EyeOff, Trash2, X } from 'lucide-react'
import { FormErrorMessage } from '../../../components/FormErrorMessage.jsx'
import {
  hideAdminNeedASubPost,
  removeAdminNeedASubPost,
  restoreAdminNeedASubPost,
} from '../shared/adminApi.js'

const REASON_MAX_LENGTH = 100

const ACTION_CONFIG = {
  hide: {
    api: hideAdminNeedASubPost,
    icon: EyeOff,
    keyPrefix: 'admin-need-a-sub-hide',
    submitLabel: 'Hide post',
    submittingLabel: 'Hiding',
    title: 'Hide post',
    tone: 'danger',
    summary: 'Hide this post from players and stop new requests.',
  },
  restore: {
    api: restoreAdminNeedASubPost,
    icon: Eye,
    keyPrefix: 'admin-need-a-sub-restore',
    submitLabel: 'Restore post',
    submittingLabel: 'Restoring',
    title: 'Restore post',
    tone: 'primary',
    summary: 'Show this post to players again.',
  },
  remove: {
    api: removeAdminNeedASubPost,
    icon: Trash2,
    keyPrefix: 'admin-need-a-sub-remove',
    submitLabel: 'Remove post',
    submittingLabel: 'Removing',
    title: 'Remove post',
    tone: 'danger',
    summary: 'Remove this post and close active requests.',
  },
}

function createActionIdempotencyKey(prefix, postId) {
  const suffix = globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random()}`
  return `${prefix}:${postId}:${suffix}`
}

function AdminNeedASubRemovalModal({
  action = 'remove',
  detail,
  firebaseUser,
  onClose,
  onCompleted,
}) {
  const config = ACTION_CONFIG[action]
  const [reason, setReason] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [executionError, setExecutionError] = useState('')
  const [idempotencyKey, setIdempotencyKey] = useState(
    () => createActionIdempotencyKey(config.keyPrefix, detail.post.id),
  )
  const Icon = config.icon

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
      const result = await config.api({
        firebaseUser,
        idempotencyKey,
        postId: detail.post.id,
        reason: reason.trim(),
      })
      onCompleted(result)
      onClose()
    } catch (error) {
      setExecutionError(error.message || 'Need a Sub post action could not be completed.')
    } finally {
      setIsSubmitting(false)
    }
  }

  function handleReasonChange(event) {
    setReason(event.target.value)
    setIdempotencyKey(createActionIdempotencyKey(config.keyPrefix, detail.post.id))
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
        <header className={`admin-sub-modal__header admin-sub-modal__header--${config.tone}`}>
          <div>
            <span className="admin-sub-modal__icon"><Icon /></span>
            <div>
              <h2 id="admin-sub-remove-title">{config.title}</h2>
            </div>
          </div>
          <button
            aria-label={`Close ${config.title}`}
            className="admin-sub-modal__close"
            disabled={isSubmitting}
            type="button"
            onClick={onClose}
          >
            <X />
          </button>
        </header>

        <form className="admin-sub-modal__form" onSubmit={handleSubmit}>
          <p>{config.summary}</p>
          <label>
            <span>Internal reason</span>
            <textarea
              disabled={isSubmitting}
              maxLength={REASON_MAX_LENGTH}
              placeholder="Required admin reason"
              value={reason}
              onChange={handleReasonChange}
            />
            <small>{reason.length}/{REASON_MAX_LENGTH}</small>
          </label>
          {executionError && (
            <div className="admin-sub-modal__message">
              <FormErrorMessage>{executionError}</FormErrorMessage>
            </div>
          )}
          <div className="admin-sub-modal__actions">
            <button
              className={
                config.tone === 'danger'
                  ? 'admin-sub-modal__danger'
                  : 'admin-sub-modal__primary'
              }
              disabled={isSubmitting || !reason.trim()}
              type="submit"
            >
              <Icon aria-hidden="true" />
              {isSubmitting ? config.submittingLabel : config.submitLabel}
            </button>
          </div>
        </form>
      </section>
    </div>
  )
}

export default AdminNeedASubRemovalModal
