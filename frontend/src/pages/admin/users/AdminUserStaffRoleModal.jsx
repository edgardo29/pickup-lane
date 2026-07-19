import { useEffect, useMemo, useState } from 'react'
import { UserCog } from 'lucide-react'
import { FormErrorMessage } from '../../../components/FormErrorMessage.jsx'
import { changeAdminUserStaffRole } from '../shared/adminApi.js'
import {
  formatAdminUserDateTime,
  formatAdminUserStatus,
} from './adminUserFormatters.js'

const STAFF_ROLE_OPTIONS = [
  { label: 'Player', value: 'player' },
  { label: 'Admin', value: 'admin' },
]

function createIdempotencyKey(userId) {
  const suffix = globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random()}`
  return `admin-user-staff-role:${userId}:${suffix}`
}

function getDefaultNextRole(currentRole) {
  if (currentRole === 'player') {
    return 'admin'
  }
  return 'player'
}

function AdminUserStaffRoleModal({
  firebaseUser,
  onChanged,
  onClose,
  user,
}) {
  const defaultNextRole = useMemo(() => getDefaultNextRole(user.role), [user.role])
  const [role, setRole] = useState(defaultNextRole)
  const [reason, setReason] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [executionError, setExecutionError] = useState('')
  const [result, setResult] = useState(null)
  const [idempotencyKey, setIdempotencyKey] = useState(
    () => createIdempotencyKey(user.id),
  )
  const isCurrentRole = role === user.role

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
    if (!reason.trim() || isCurrentRole || isSubmitting) {
      return
    }

    setIsSubmitting(true)
    setExecutionError('')

    try {
      const nextResult = await changeAdminUserStaffRole({
        firebaseUser,
        idempotencyKey,
        reason: reason.trim(),
        role,
        userId: user.id,
      })
      setResult(nextResult)
      onChanged(nextResult)
    } catch (error) {
      setExecutionError(error.message || 'Staff role could not be changed.')
    } finally {
      setIsSubmitting(false)
    }
  }

  function handleBackdropClick() {
    if (!isSubmitting) {
      onClose()
    }
  }

  function handleRoleChange(event) {
    setRole(event.target.value)
    setIdempotencyKey(createIdempotencyKey(user.id))
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
        className="admin-user-suspension-modal admin-user-suspension-modal--staff"
        role="dialog"
        aria-modal="true"
        aria-labelledby="admin-user-staff-role-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="admin-user-suspension-modal__header">
          <span><UserCog /></span>
          <div>
            <h2 id="admin-user-staff-role-title">
              {result ? 'Role changed' : 'Change staff role?'}
            </h2>
            <p>{user.display_name}</p>
          </div>
        </header>

        {!result && (
          <form className="admin-user-suspension-modal__form" onSubmit={handleSubmit}>
            <p>
              Staff access changes immediately. The last active admin cannot be
              demoted.
            </p>
            <label>
              <span>New role</span>
              <select
                disabled={isSubmitting}
                value={role}
                onChange={handleRoleChange}
              >
                {STAFF_ROLE_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>Internal reason</span>
              <textarea
                disabled={isSubmitting}
                maxLength={500}
                placeholder="Required staff role change reason"
                value={reason}
                onChange={handleReasonChange}
              />
              <small>{reason.length}/500</small>
            </label>
            {isCurrentRole && (
              <div className="admin-user-suspension-modal__message">
                <FormErrorMessage>
                  Choose a role different from the current role.
                </FormErrorMessage>
              </div>
            )}
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
                disabled={isSubmitting || isCurrentRole || !reason.trim()}
                type="submit"
              >
                {isSubmitting ? 'Changing' : 'Change role'}
              </button>
            </div>
          </form>
        )}

        {result && (
          <div className="admin-user-suspension-modal__result">
            <strong>
              {user.display_name} is now {formatAdminUserStatus(result.role)}.
            </strong>
            <p>
              Role changed from {formatAdminUserStatus(result.previous_role)}
              {' '}at {formatAdminUserDateTime(result.changed_at)}.
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

export default AdminUserStaffRoleModal
