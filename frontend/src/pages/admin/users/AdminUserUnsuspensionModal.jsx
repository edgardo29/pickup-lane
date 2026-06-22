import { useEffect, useState } from 'react'
import { ShieldCheck } from 'lucide-react'
import { FormErrorMessage } from '../../../components/FormErrorMessage.jsx'
import { unsuspendAdminUser } from '../shared/adminApi.js'
import { formatAdminUserDateTime } from './adminUserFormatters.js'

function createIdempotencyKey(userId) {
  const suffix = globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random()}`
  return `admin-user-unsuspend:${userId}:${suffix}`
}

function AdminUserUnsuspensionModal({
  firebaseUser,
  onClose,
  onUnsuspended,
  user,
}) {
  const [reason, setReason] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [executionError, setExecutionError] = useState('')
  const [result, setResult] = useState(null)
  const [idempotencyKey, setIdempotencyKey] = useState(
    () => createIdempotencyKey(user.id),
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
      const nextResult = await unsuspendAdminUser({
        firebaseUser,
        idempotencyKey,
        reason: reason.trim(),
        userId: user.id,
      })
      setResult(nextResult)
      onUnsuspended(nextResult)
    } catch (error) {
      setExecutionError(error.message || 'The account could not be unsuspended.')
    } finally {
      setIsSubmitting(false)
    }
  }

  function handleBackdropClick() {
    if (!isSubmitting) {
      onClose()
    }
  }

  function handleReasonChange(event) {
    setReason(event.target.value)
    setIdempotencyKey(createIdempotencyKey(user.id))
  }

  return (
    <div
      className="admin-user-suspension-backdrop"
      role="presentation"
      onClick={handleBackdropClick}
    >
      <section
        className="admin-user-suspension-modal admin-user-suspension-modal--restore"
        role="dialog"
        aria-modal="true"
        aria-labelledby="admin-user-unsuspension-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="admin-user-suspension-modal__header">
          <span><ShieldCheck /></span>
          <div>
            <h2 id="admin-user-unsuspension-title">
              {result ? 'Account restored' : 'Unsuspend account?'}
            </h2>
            <p>{user.display_name}</p>
          </div>
        </header>

        {!result && (
          <form className="admin-user-suspension-modal__form" onSubmit={handleSubmit}>
            <p>
              The account will return to active status. Hosting access will remain
              governed by the user&apos;s current hosting status.
            </p>
            <label>
              <span>Internal reason</span>
              <textarea
                disabled={isSubmitting}
                maxLength={500}
                placeholder="Required unsuspension reason"
                value={reason}
                onChange={handleReasonChange}
              />
              <small>{reason.length}/500</small>
            </label>
            {executionError && (
              <div className="admin-user-suspension-modal__message">
                <FormErrorMessage>{executionError}</FormErrorMessage>
              </div>
            )}
            <div className="admin-user-suspension-modal__actions">
              <button
                className="admin-user-suspension-modal__secondary"
                disabled={isSubmitting}
                type="button"
                onClick={onClose}
              >
                Back
              </button>
              <button
                className="admin-user-suspension-modal__restore"
                disabled={isSubmitting || !reason.trim()}
                type="submit"
              >
                {isSubmitting ? 'Restoring' : 'Unsuspend account'}
              </button>
            </div>
          </form>
        )}

        {result && (
          <div className="admin-user-suspension-modal__result">
            <strong>{user.display_name} is active again.</strong>
            <p>
              Account access was restored at{' '}
              {formatAdminUserDateTime(result.unsuspended_at)}.
            </p>
            <div className="admin-user-suspension-modal__actions">
              <button
                className="admin-user-suspension-modal__secondary"
                type="button"
                onClick={onClose}
              >
                Close
              </button>
            </div>
          </div>
        )}
      </section>
    </div>
  )
}

export default AdminUserUnsuspensionModal
