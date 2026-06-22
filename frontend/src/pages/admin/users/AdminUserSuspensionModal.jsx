import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ShieldBan } from 'lucide-react'
import { FormErrorMessage } from '../../../components/FormErrorMessage.jsx'
import {
  previewAdminUserSuspension,
  suspendAdminUser,
} from '../shared/adminApi.js'
import {
  formatAdminUserDateTime,
  formatAdminUserStatus,
} from './adminUserFormatters.js'

function createIdempotencyKey(userId) {
  const suffix = globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random()}`
  return `admin-user-suspend:${userId}:${suffix}`
}

function fetchSuspensionPreview(firebaseUser, userId) {
  return previewAdminUserSuspension({ firebaseUser, userId })
}

function AdminUserSuspensionModal({
  canOpenOfficialGames,
  firebaseUser,
  onClose,
  onSuspended,
  user,
}) {
  const [preview, setPreview] = useState(null)
  const [loadState, setLoadState] = useState('loading')
  const [previewError, setPreviewError] = useState('')
  const [executionError, setExecutionError] = useState('')
  const [reason, setReason] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [result, setResult] = useState(null)
  const [idempotencyKey, setIdempotencyKey] = useState(
    () => createIdempotencyKey(user.id),
  )

  useEffect(() => {
    let isMounted = true

    async function loadInitialPreview() {
      try {
        const nextPreview = await fetchSuspensionPreview(firebaseUser, user.id)
        if (!isMounted) {
          return
        }
        setPreview(nextPreview)
        setLoadState('ready')
      } catch (error) {
        if (!isMounted) {
          return
        }
        setPreview(null)
        setPreviewError(error.message || 'Suspension impact could not be loaded.')
        setLoadState('error')
      }
    }

    loadInitialPreview()
    return () => {
      isMounted = false
    }
  }, [firebaseUser, user.id])

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
    if (!preview?.can_suspend || !reason.trim() || isSubmitting) {
      return
    }

    setIsSubmitting(true)
    setExecutionError('')

    try {
      const nextResult = await suspendAdminUser({
        firebaseUser,
        idempotencyKey,
        previewToken: preview.preview_token,
        reason: reason.trim(),
        userId: user.id,
      })
      setResult(nextResult)
      onSuspended(nextResult)
    } catch (error) {
      setExecutionError(error.message || 'The account could not be suspended.')
    } finally {
      setIsSubmitting(false)
    }
  }

  async function handleRefreshPreview() {
    setIdempotencyKey(createIdempotencyKey(user.id))
    setLoadState('loading')
    setPreview(null)
    setPreviewError('')
    setExecutionError('')

    try {
      const nextPreview = await fetchSuspensionPreview(firebaseUser, user.id)
      setPreview(nextPreview)
      setLoadState('ready')
    } catch (error) {
      setPreview(null)
      setPreviewError(error.message || 'Suspension impact could not be loaded.')
      setLoadState('error')
    }
  }

  function handleReasonChange(event) {
    setReason(event.target.value)
    setIdempotencyKey(createIdempotencyKey(user.id))
  }

  function handleBackdropClick() {
    if (!isSubmitting) {
      onClose()
    }
  }

  return (
    <div
      className="admin-user-suspension-backdrop"
      role="presentation"
      onClick={handleBackdropClick}
    >
      <section
        className="admin-user-suspension-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="admin-user-suspension-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="admin-user-suspension-modal__header">
          <span><ShieldBan /></span>
          <div>
            <h2 id="admin-user-suspension-title">
              {result ? 'Account suspended' : 'Suspend account?'}
            </h2>
            <p>{user.display_name}</p>
          </div>
        </header>

        {loadState === 'loading' && !result && (
          <p className="admin-user-suspension-modal__loading" role="status">
            Loading suspension impact.
          </p>
        )}

        {previewError && (
          <div className="admin-user-suspension-modal__message">
            <FormErrorMessage>{previewError}</FormErrorMessage>
            <button type="button" onClick={handleRefreshPreview}>
              Retry
            </button>
          </div>
        )}

        {preview && !result && (
          <>
            <div className="admin-user-suspension-modal__facts">
              <div>
                <span>Current account</span>
                <strong>{formatAdminUserStatus(preview.account_status)}</strong>
              </div>
              <div>
                <span>Role</span>
                <strong>{formatAdminUserStatus(preview.role)}</strong>
              </div>
              <div>
                <span>Official host blockers</span>
                <strong>{preview.future_official_host_assignment_count}</strong>
              </div>
            </div>

            {preview.blocking_reasons.length > 0 && (
              <div className="admin-user-suspension-modal__warning">
                <strong>Suspension is blocked</strong>
                {preview.blocking_reasons.map((blockingReason) => (
                  <p key={blockingReason}>{blockingReason}</p>
                ))}
              </div>
            )}

            {preview.future_official_host_assignments.length > 0 && (
              <div className="admin-user-suspension-modal__assignments">
                <h3>Future official host assignments</h3>
                {preview.future_official_host_assignments.map((game) => (
                  <div key={game.id}>
                    <span>
                      <strong>{game.title}</strong>
                      <small>
                        {formatAdminUserDateTime(game.starts_at)}
                        {' · '}
                        {game.city}, {game.state}
                      </small>
                    </span>
                    {canOpenOfficialGames && (
                      <Link to={`/admin/official-games/${game.id}`} onClick={onClose}>
                        Open game
                      </Link>
                    )}
                  </div>
                ))}
                {preview.future_official_host_assignment_count
                  > preview.future_official_host_assignments.length && (
                  <p>
                    Showing the first {preview.future_official_host_assignments.length}
                    {' '}assignments.
                  </p>
                )}
              </div>
            )}

            {preview.can_suspend && (
              <form className="admin-user-suspension-modal__form" onSubmit={handleSubmit}>
                <p>
                  The user will lose access to product and staff actions. Their
                  historical records will remain available.
                </p>
                <label>
                  <span>Internal reason</span>
                  <textarea
                    disabled={isSubmitting}
                    maxLength={500}
                    placeholder="Required suspension reason"
                    value={reason}
                    onChange={handleReasonChange}
                  />
                  <small>{reason.length}/500</small>
                </label>
                {executionError && (
                  <div className="admin-user-suspension-modal__message">
                    <FormErrorMessage>{executionError}</FormErrorMessage>
                    <button type="button" onClick={handleRefreshPreview}>
                      Refresh impact
                    </button>
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
                    className="admin-user-suspension-modal__danger"
                    disabled={isSubmitting || !reason.trim()}
                    type="submit"
                  >
                    {isSubmitting ? 'Suspending' : 'Suspend account'}
                  </button>
                </div>
              </form>
            )}

            {!preview.can_suspend && (
              <div className="admin-user-suspension-modal__actions">
                <button
                  className="admin-user-suspension-modal__secondary"
                  type="button"
                  onClick={onClose}
                >
                  Close
                </button>
                <button
                  className="admin-user-suspension-modal__secondary"
                  type="button"
                  onClick={handleRefreshPreview}
                >
                  Refresh impact
                </button>
              </div>
            )}
          </>
        )}

        {result && (
          <div className="admin-user-suspension-modal__result">
            <strong>{user.display_name} is now suspended.</strong>
            <p>
              Suspension completed at{' '}
              {formatAdminUserDateTime(result.suspended_at)}.
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

export default AdminUserSuspensionModal
