import { useEffect, useState } from 'react'
import { EyeOff, X } from 'lucide-react'
import { FormErrorMessage } from '../../../components/FormErrorMessage.jsx'
import { hideAdminCommunityGamePaymentText } from '../shared/adminApi.js'

const REASON_MAX_LENGTH = 100

function createHidePaymentTextIdempotencyKey(gameId) {
  const suffix = globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random()}`
  return `admin-community-hide-payment-text:${gameId}:${suffix}`
}

function AdminCommunityGameHidePaymentTextModal({
  detail,
  firebaseUser,
  onClose,
  onHidden,
}) {
  const [reason, setReason] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [executionError, setExecutionError] = useState('')
  const [idempotencyKey, setIdempotencyKey] = useState(
    () => createHidePaymentTextIdempotencyKey(detail.game.id),
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
      const result = await hideAdminCommunityGamePaymentText({
        firebaseUser,
        gameId: detail.game.id,
        idempotencyKey,
        reason: reason.trim(),
      })
      onHidden(result)
      onClose()
    } catch (error) {
      setExecutionError(error.message || 'Payment text could not be hidden.')
    } finally {
      setIsSubmitting(false)
    }
  }

  function handleReasonChange(event) {
    setReason(event.target.value)
    setIdempotencyKey(createHidePaymentTextIdempotencyKey(detail.game.id))
  }

  function handleBackdropClick() {
    if (!isSubmitting) {
      onClose()
    }
  }

  return (
    <div
      className="admin-community-modal-backdrop"
      role="presentation"
      onClick={handleBackdropClick}
    >
      <section
        aria-labelledby="admin-community-hide-payment-title"
        aria-modal="true"
        className="admin-community-modal"
        role="dialog"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="admin-community-modal__header">
          <div>
            <span className="admin-community-modal__icon"><EyeOff /></span>
            <div>
              <h2 id="admin-community-hide-payment-title">Hide payment info</h2>
            </div>
          </div>
          <button
            aria-label="Close hide payment info"
            className="admin-community-modal__close"
            disabled={isSubmitting}
            type="button"
            onClick={onClose}
          >
            <X />
          </button>
        </header>

        <form className="admin-community-modal__form" onSubmit={handleSubmit}>
          <p>Hides this host payment info from player-facing game details.</p>
          <label>
            <span>Internal reason</span>
            <textarea
              disabled={isSubmitting}
              maxLength={REASON_MAX_LENGTH}
              placeholder="Required moderation reason"
              value={reason}
              onChange={handleReasonChange}
            />
            <small>{reason.length}/{REASON_MAX_LENGTH}</small>
          </label>
          {executionError && (
            <div className="admin-community-modal__message">
              <FormErrorMessage>{executionError}</FormErrorMessage>
            </div>
          )}
          <div className="admin-community-modal__actions">
            <button
              className="admin-community-modal__danger"
              disabled={isSubmitting || !reason.trim()}
              type="submit"
            >
              <EyeOff aria-hidden="true" />
              {isSubmitting ? 'Hiding' : 'Hide payment info'}
            </button>
          </div>
        </form>
      </section>
    </div>
  )
}

export default AdminCommunityGameHidePaymentTextModal
