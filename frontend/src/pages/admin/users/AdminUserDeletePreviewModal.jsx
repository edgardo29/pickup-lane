import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Trash2 } from 'lucide-react'
import { FormErrorMessage } from '../../../components/FormErrorMessage.jsx'
import {
  deleteAdminUser,
  previewAdminUserDeleteImpact,
} from '../shared/adminApi.js'
import {
  formatAdminUserDateTime,
  formatAdminUserStatus,
} from './adminUserFormatters.js'

function buildImpactRows(preview) {
  return [
    {
      label: 'Active future bookings',
      value: preview.active_future_booking_count,
      description: `${preview.active_future_official_booking_count} official bookings`,
    },
    {
      label: 'Roster participations',
      value: preview.active_future_participation_count,
      description: 'Future active roster rows for this user',
    },
    {
      label: 'Guest rows',
      value: preview.active_future_guest_count,
      description: 'Future guest rows attached to this user',
    },
    {
      label: 'Waitlist entries',
      value: preview.active_waitlist_entry_count,
      description: 'Active, promoted, processing, or accepted waitlist rows',
    },
    {
      label: 'Need a Sub posts',
      value: preview.active_owned_sub_post_count,
      description: 'Active or filled posts owned by this user',
    },
    {
      label: 'Need a Sub requests',
      value: preview.active_sub_request_count,
      description: 'Pending, confirmed, or waitlisted requests',
    },
    {
      label: 'Payments',
      value: preview.payment_record_count,
      description: 'Stripe-backed payment records',
    },
    {
      label: 'Refunds',
      value: preview.refund_record_count,
      description: 'Refund records linked to this user',
    },
    {
      label: 'Credits',
      value: preview.game_credit_count,
      description: 'Pickup Lane game credit records',
    },
    {
      label: 'Saved cards',
      value: preview.saved_payment_method_count,
      description: `${preview.active_saved_payment_method_count} active saved cards`,
    },
    {
      label: 'Open support flags',
      value: preview.active_support_flag_count,
      description: 'Active support follow-up rows',
    },
  ]
}

function createIdempotencyKey(userId) {
  const suffix = globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random()}`
  return `admin-user-delete:${userId}:${suffix}`
}

function DeletePreviewGameList({
  canOpenOfficialGames,
  count,
  games,
  onClose,
  title,
}) {
  if (!games.length) {
    return null
  }

  return (
    <div className="admin-user-suspension-modal__assignments">
      <h3>{title}</h3>
      {games.map((game) => (
        <div key={game.id}>
          <span>
            <strong>{game.title}</strong>
            <small>
              {formatAdminUserDateTime(game.starts_at)}
              {' - '}
              {game.city}, {game.state}
            </small>
          </span>
          {canOpenOfficialGames && game.game_type === 'official' ? (
            <Link to={`/admin/official-games/${game.id}`} onClick={onClose}>
              Open game
            </Link>
          ) : (
            <small>{formatAdminUserStatus(game.game_status)}</small>
          )}
        </div>
      ))}
      {count > games.length && (
        <p>Showing the first {games.length} games.</p>
      )}
    </div>
  )
}

function AdminUserDeletePreviewModal({
  canOpenOfficialGames,
  firebaseUser,
  onClose,
  onDeleted,
  user,
}) {
  const [preview, setPreview] = useState(null)
  const [loadState, setLoadState] = useState('loading')
  const [previewError, setPreviewError] = useState('')
  const [executionError, setExecutionError] = useState('')
  const [reason, setReason] = useState('')
  const [confirmationText, setConfirmationText] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [result, setResult] = useState(null)
  const [displayName] = useState(() => user.display_name)
  const [idempotencyKey, setIdempotencyKey] = useState(
    () => createIdempotencyKey(user.id),
  )

  useEffect(() => {
    let isMounted = true

    async function loadPreview() {
      try {
        const nextPreview = await previewAdminUserDeleteImpact({
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
        setPreviewError(error.message || 'Delete impact could not be loaded.')
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

  async function handleSubmit(event) {
    event.preventDefault()
    if (
      !preview?.can_delete
      || !reason.trim()
      || confirmationText.trim().toUpperCase() !== 'DELETE'
      || isSubmitting
    ) {
      return
    }

    setIsSubmitting(true)
    setExecutionError('')

    try {
      const nextResult = await deleteAdminUser({
        firebaseUser,
        idempotencyKey,
        previewToken: preview.preview_token,
        reason: reason.trim(),
        userId: user.id,
      })
      setResult(nextResult)
      onDeleted?.(nextResult)
    } catch (error) {
      setExecutionError(error.message || 'The account could not be deleted.')
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
    setConfirmationText('')

    try {
      const nextPreview = await previewAdminUserDeleteImpact({
        firebaseUser,
        userId: user.id,
      })
      setPreview(nextPreview)
      setLoadState('ready')
    } catch (error) {
      setPreview(null)
      setPreviewError(error.message || 'Delete impact could not be loaded.')
      setLoadState('error')
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

  const impactRows = preview ? buildImpactRows(preview) : []

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
        aria-labelledby="admin-user-delete-preview-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="admin-user-suspension-modal__header">
          <span><Trash2 /></span>
          <div>
            <h2 id="admin-user-delete-preview-title">
              {result ? 'Account deleted' : 'Delete account?'}
            </h2>
            <p>{displayName}</p>
          </div>
        </header>

        {loadState === 'loading' && !result && (
          <>
            <p className="admin-user-suspension-modal__loading" role="status">
              Loading delete impact.
            </p>
            <div className="admin-user-suspension-modal__actions">
              <button
                className="admin-user-suspension-modal__secondary"
                type="button"
                onClick={onClose}
              >
                Back
              </button>
            </div>
          </>
        )}

        {previewError && !result && (
          <>
            <div className="admin-user-suspension-modal__message">
              <FormErrorMessage>{previewError}</FormErrorMessage>
            </div>
            <div className="admin-user-suspension-modal__actions">
              <button
                className="admin-user-suspension-modal__secondary"
                type="button"
                onClick={onClose}
              >
                Back
              </button>
              <button
                className="admin-user-suspension-modal__secondary"
                type="button"
                onClick={handleRefreshPreview}
              >
                Retry
              </button>
            </div>
          </>
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
                <span>Delete blocked</span>
                <strong>{preview.can_delete ? 'No' : 'Yes'}</strong>
              </div>
            </div>

            {preview.blocking_reasons.length > 0 && (
              <div className="admin-user-suspension-modal__warning">
                <strong>Delete is blocked</strong>
                {preview.blocking_reasons.map((blockingReason) => (
                  <p key={blockingReason}>{blockingReason}</p>
                ))}
              </div>
            )}

            <DeletePreviewGameList
              canOpenOfficialGames={canOpenOfficialGames}
              count={preview.future_official_host_assignment_count}
              games={preview.future_official_host_assignments}
              onClose={onClose}
              title="Future official host blockers"
            />

            <DeletePreviewGameList
              canOpenOfficialGames={false}
              count={preview.future_community_hosted_game_count}
              games={preview.future_community_hosted_games}
              onClose={onClose}
              title="Future community hosted games"
            />

            <div className="admin-user-suspension-modal__assignments">
              <h3>Impacted records</h3>
              {impactRows.map((row) => (
                <div key={row.label}>
                  <span>
                    <strong>{row.label}</strong>
                    <small>{row.description}</small>
                  </span>
                  <small>{row.value}</small>
                </div>
              ))}
            </div>

            {preview.can_delete ? (
              <form className="admin-user-suspension-modal__form" onSubmit={handleSubmit}>
                <p>
                  This will anonymize the app user, remove saved cards, cancel future
                  roster, waitlist, and hosted community game activity, and preserve
                  booking, money, audit, and history records.
                </p>
                <label>
                  <span>Internal reason</span>
                  <textarea
                    disabled={isSubmitting}
                    maxLength={500}
                    placeholder="Required deletion reason"
                    value={reason}
                    onChange={handleReasonChange}
                  />
                  <small>{reason.length}/500</small>
                </label>
                <label>
                  <span>Type DELETE</span>
                  <input
                    autoComplete="off"
                    disabled={isSubmitting}
                    value={confirmationText}
                    onChange={(event) => setConfirmationText(event.target.value)}
                  />
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
                    disabled={
                      isSubmitting
                      || !reason.trim()
                      || confirmationText.trim().toUpperCase() !== 'DELETE'
                    }
                    type="submit"
                  >
                    {isSubmitting ? 'Deleting' : 'Delete account'}
                  </button>
                </div>
              </form>
            ) : (
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
            <strong>{displayName} has been deleted.</strong>
            <p>
              Deletion completed at{' '}
              {formatAdminUserDateTime(result.deleted_at)}.
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

export default AdminUserDeletePreviewModal
