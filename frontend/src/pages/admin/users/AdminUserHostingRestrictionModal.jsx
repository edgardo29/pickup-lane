import { useEffect, useState } from 'react'
import { ShieldOff } from 'lucide-react'
import { FormErrorMessage } from '../../../components/FormErrorMessage.jsx'
import {
  previewAdminUserHostingRestriction,
  restrictAdminUserHosting,
} from '../shared/adminApi.js'
import {
  formatAdminUserDateTime,
  formatAdminUserStatus,
} from './adminUserFormatters.js'

function createIdempotencyKey(userId) {
  const suffix = globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random()}`
  return `admin-user-restrict-hosting:${userId}:${suffix}`
}

function AdminUserHostingRestrictionModal({
  firebaseUser,
  onClose,
  onRestricted,
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

    async function loadPreview() {
      try {
        const nextPreview = await previewAdminUserHostingRestriction({
          firebaseUser,
          userId: user.id,
        })
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
        setPreviewError(error.message || 'Hosting impact could not be loaded.')
        setLoadState('error')
      }
    }

    loadPreview()
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

  async function handleRefreshPreview() {
    setIdempotencyKey(createIdempotencyKey(user.id))
    setLoadState('loading')
    setPreview(null)
    setPreviewError('')
    setExecutionError('')

    try {
      const nextPreview = await previewAdminUserHostingRestriction({
        firebaseUser,
        userId: user.id,
      })
      setPreview(nextPreview)
      setLoadState('ready')
    } catch (error) {
      setPreview(null)
      setPreviewError(error.message || 'Hosting impact could not be loaded.')
      setLoadState('error')
    }
  }

  async function handleSubmit(event) {
    event.preventDefault()
    if (!preview?.can_restrict || !reason.trim() || isSubmitting) {
      return
    }

    setIsSubmitting(true)
    setExecutionError('')

    try {
      const nextResult = await restrictAdminUserHosting({
        firebaseUser,
        idempotencyKey,
        previewToken: preview.preview_token,
        reason: reason.trim(),
        userId: user.id,
      })
      setResult(nextResult)
      onRestricted(nextResult)
    } catch (error) {
      setExecutionError(error.message || 'Hosting could not be restricted.')
    } finally {
      setIsSubmitting(false)
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
        className="admin-user-suspension-modal admin-user-suspension-modal--hosting"
        role="dialog"
        aria-modal="true"
        aria-labelledby="admin-user-hosting-restriction-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="admin-user-suspension-modal__header">
          <span><ShieldOff /></span>
          <div>
            <h2 id="admin-user-hosting-restriction-title">
              {result ? 'Hosting restricted' : 'Restrict hosting?'}
            </h2>
            <p>{user.display_name}</p>
          </div>
        </header>

        {loadState === 'loading' && !result && (
          <p className="admin-user-suspension-modal__loading" role="status">
            Loading hosting impact.
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
                <span>Current hosting</span>
                <strong>{formatAdminUserStatus(preview.hosting_status)}</strong>
              </div>
              <div>
                <span>Future games</span>
                <strong>{preview.future_community_game_count}</strong>
              </div>
            </div>

            {preview.blocking_reasons.length > 0 && (
              <div className="admin-user-suspension-modal__warning">
                <strong>Hosting restriction is blocked</strong>
                {preview.blocking_reasons.map((blockingReason) => (
                  <p key={blockingReason}>{blockingReason}</p>
                ))}
              </div>
            )}

            {preview.future_community_games.length > 0 && (
              <div className="admin-user-suspension-modal__assignments">
                <h3>Future community games</h3>
                {preview.future_community_games.map((game) => (
                  <div key={game.id}>
                    <span>
                      <strong>{game.title}</strong>
                      <small>
                        {formatAdminUserDateTime(game.starts_at)}
                        {' · '}
                        {game.city}, {game.state}
                      </small>
                    </span>
                    <small>{formatAdminUserStatus(game.game_status)}</small>
                  </div>
                ))}
                {preview.future_community_game_count
                  > preview.future_community_games.length && (
                  <p>
                    Showing the first {preview.future_community_games.length}
                    {' '}games.
                  </p>
                )}
              </div>
            )}

            {preview.can_restrict && (
              <form className="admin-user-suspension-modal__form" onSubmit={handleSubmit}>
                <p>
                  The user will not be able to publish new community games.
                  Existing hosted games stay active and manageable.
                </p>
                <label>
                  <span>Internal reason</span>
                  <textarea
                    disabled={isSubmitting}
                    maxLength={500}
                    placeholder="Required hosting restriction reason"
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
                    {isSubmitting ? 'Restricting' : 'Restrict hosting'}
                  </button>
                </div>
              </form>
            )}

            {!preview.can_restrict && (
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
            <strong>{user.display_name} cannot publish new community games.</strong>
            <p>
              Hosting was restricted at{' '}
              {formatAdminUserDateTime(result.restricted_at)}.
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

export default AdminUserHostingRestrictionModal
