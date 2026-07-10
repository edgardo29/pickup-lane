import { useEffect, useState } from 'react'
import { CheckCircle2, ClipboardList, X } from 'lucide-react'
import { FormErrorMessage } from '../../../components/FormErrorMessage.jsx'
import {
  flagAdminCommunityGameForReview,
  resolveAdminSupportFlag,
} from '../shared/adminApi.js'

const RESOLUTION_OPTIONS = [
  { label: 'Handled externally', value: 'handled_externally' },
  { label: 'No action needed', value: 'no_action_needed' },
  { label: 'Duplicate flag', value: 'duplicate' },
  { label: 'Invalid flag', value: 'invalid_flag' },
]
const REASON_MAX_LENGTH = 100

function createReviewFlagIdempotencyKey(gameId) {
  const suffix = globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random()}`
  return `admin-community-review:${gameId}:${suffix}`
}

function createReviewResolutionIdempotencyKey(flagId) {
  const suffix = globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random()}`
  return `admin-community-review-resolve:${flagId}:${suffix}`
}

function AdminCommunityGameReviewModal({
  detail,
  firebaseUser,
  flag = null,
  onClose,
  onCompleted,
}) {
  const isResolving = Boolean(flag)
  const [reason, setReason] = useState('')
  const [outcome, setOutcome] = useState('handled_externally')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [executionError, setExecutionError] = useState('')
  const [idempotencyKey, setIdempotencyKey] = useState(
    () => (
      flag
        ? createReviewResolutionIdempotencyKey(flag.id)
        : createReviewFlagIdempotencyKey(detail.game.id)
    ),
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
      const result = isResolving
        ? await resolveAdminSupportFlag({
            firebaseUser,
            idempotencyKey,
            outcome,
            reason: reason.trim(),
            supportFlagId: flag.id,
          })
        : await flagAdminCommunityGameForReview({
            firebaseUser,
            gameId: detail.game.id,
            idempotencyKey,
            reason: reason.trim(),
          })
      onCompleted(result)
      onClose()
    } catch (error) {
      setExecutionError(
        error.message ||
          (isResolving
            ? 'Review flag could not be resolved.'
            : 'Community game could not be flagged.'),
      )
    } finally {
      setIsSubmitting(false)
    }
  }

  function handleReasonChange(event) {
    setReason(event.target.value)
    if (!isResolving) {
      setIdempotencyKey(createReviewFlagIdempotencyKey(detail.game.id))
    }
  }

  function handleBackdropClick() {
    if (!isSubmitting) {
      onClose()
    }
  }

  const Icon = isResolving ? CheckCircle2 : ClipboardList
  const title = isResolving ? 'Resolve review flag' : 'Flag for review'

  return (
    <div
      className="admin-community-modal-backdrop"
      role="presentation"
      onClick={handleBackdropClick}
    >
      <section
        aria-labelledby="admin-community-review-title"
        aria-modal="true"
        className="admin-community-modal"
        role="dialog"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="admin-community-modal__header admin-community-modal__header--review">
          <div>
            <span className="admin-community-modal__icon"><Icon /></span>
            <div>
              <h2 id="admin-community-review-title">{title}</h2>
            </div>
          </div>
          <button
            aria-label={`Close ${title}`}
            className="admin-community-modal__close"
            disabled={isSubmitting}
            type="button"
            onClick={onClose}
          >
            <X />
          </button>
        </header>

        <form className="admin-community-modal__form" onSubmit={handleSubmit}>
          <p>
            {isResolving
              ? flag.summary
              : 'Creates an internal follow-up flag for admin review.'}
          </p>
          {isResolving && (
            <label>
              <span>Outcome</span>
              <select
                disabled={isSubmitting}
                value={outcome}
                onChange={(event) => setOutcome(event.target.value)}
              >
                {RESOLUTION_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
          )}
          <label>
            <span>{isResolving ? 'Resolution reason' : 'Review reason'}</span>
            <textarea
              disabled={isSubmitting}
              maxLength={REASON_MAX_LENGTH}
              placeholder="Required internal reason"
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
              className="admin-community-modal__primary"
              disabled={isSubmitting || !reason.trim()}
              type="submit"
            >
              <Icon aria-hidden="true" />
              {isSubmitting
                ? isResolving ? 'Resolving' : 'Flagging'
                : isResolving ? 'Resolve flag' : 'Flag game'}
            </button>
          </div>
        </form>
      </section>
    </div>
  )
}

export default AdminCommunityGameReviewModal
