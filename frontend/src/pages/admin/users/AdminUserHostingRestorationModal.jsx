import { useEffect, useState } from 'react'
import { ShieldCheck } from 'lucide-react'
import { FormErrorMessage } from '../../../components/FormErrorMessage.jsx'
import { restoreAdminUserHosting } from '../shared/adminApi.js'
import { formatAdminUserDateTime } from './adminUserFormatters.js'

function createIdempotencyKey(userId) {
  const suffix = globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random()}`
  return `admin-user-restore-hosting:${userId}:${suffix}`
}

function AdminUserHostingRestorationModal({
  firebaseUser,
  onClose,
  onRestored,
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
      const nextResult = await restoreAdminUserHosting({
        firebaseUser,
        idempotencyKey,
        reason: reason.trim(),
        userId: user.id,
      })
      setResult(nextResult)
      onRestored(nextResult)
    } catch (error) {
      setExecutionError(error.message || 'Hosting access could not be restored.')
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
        aria-labelledby="admin-user-hosting-restoration-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="admin-user-suspension-modal__header">
          <span><ShieldCheck /></span>
          <div>
            <h2 id="admin-user-hosting-restoration-title">
              {result ? 'Hosting restored' : 'Restore hosting?'}
            </h2>
            <p>{user.display_name}</p>
          </div>
        </header>

        {!result && (
          <form className="admin-user-suspension-modal__form" onSubmit={handleSubmit}>
            <p>
              Hosting access will return to eligible. Account status and existing
              hosted games will not change.
            </p>
            <label>
              <span>Internal reason</span>
              <textarea
                disabled={isSubmitting}
                maxLength={500}
                placeholder="Required hosting restoration reason"
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
                {isSubmitting ? 'Restoring' : 'Restore hosting'}
              </button>
            </div>
          </form>
        )}

        {result && (
          <div className="admin-user-suspension-modal__result">
            <strong>{user.display_name} has eligible hosting access again.</strong>
            <p>
              Hosting access was restored at{' '}
              {formatAdminUserDateTime(result.restored_at)}.
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

export default AdminUserHostingRestorationModal
