import { PasswordField } from './ProfileFields.jsx'
import { BellIcon, KeyIcon, TrashIcon } from './ProfileIcons.jsx'
import { dismissOnBackdropMouseDown, useDismissibleModal } from './useModalBodyLock.js'

export function DeleteAccountModal({
  deleteConfirmation,
  deleteError,
  deleteStatus,
  onCancel,
  onConfirmationChange,
  onSubmit,
}) {
  const handleCancel = () => {
    if (deleteStatus !== 'deleting' && deleteStatus !== 'success') {
      onCancel()
    }
  }

  useDismissibleModal(handleCancel)

  return (
    <div
      className="settings-modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby="delete-account-title"
      onMouseDown={(event) => dismissOnBackdropMouseDown(event, handleCancel)}
    >
      <form className="settings-modal__card" onSubmit={onSubmit}>
        {deleteStatus === 'success' && (
          <p className="settings-modal__success" role="status">
            Account deleted successfully!
          </p>
        )}

        <div className="settings-modal__header">
          <div>
            <h2 className="settings-modal__title" id="delete-account-title">
              <span className="settings-modal__title-icon settings-modal__title-icon--danger" aria-hidden="true">
                <TrashIcon />
              </span>
              <span>Delete account</span>
            </h2>
            <p className="settings-modal__subtitle">This will sign you out and delete your Pickup Lane profile.</p>
          </div>
        </div>

        <label className="profile-edit-field">
          <span className="settings-delete-label">
            Type <strong>"delete"</strong> to confirm
          </span>
          <input
            autoComplete="off"
            onChange={(event) => onConfirmationChange(event.target.value)}
            placeholder="delete"
            spellCheck="false"
            value={deleteConfirmation}
          />
        </label>

        {deleteError && <p className="profile-edit-error">{deleteError}</p>}

        <div className="settings-modal__actions">
          <button
            className="profile-edit-cancel"
            disabled={deleteStatus === 'deleting' || deleteStatus === 'success'}
            onClick={handleCancel}
            type="button"
          >
            Back
          </button>
          <button
            className="profile-primary-action profile-primary-action--danger"
            disabled={
              deleteStatus === 'deleting' ||
              deleteStatus === 'success' ||
              deleteConfirmation.trim().toLowerCase() !== 'delete'
            }
            type="submit"
          >
            {deleteStatus === 'deleting' ? 'Deleting...' : 'Delete account'}
          </button>
        </div>
      </form>
    </div>
  )
}

export function NotificationSettingsModal({
  emailNotificationsEnabled,
  notificationError,
  notificationStatus,
  onCancel,
  onEmailNotificationsChange,
  onSubmit,
}) {
  const handleCancel = () => {
    if (notificationStatus !== 'saving') {
      onCancel()
    }
  }

  useDismissibleModal(handleCancel)

  return (
    <div
      className="settings-modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby="notification-settings-title"
      onMouseDown={(event) => dismissOnBackdropMouseDown(event, handleCancel)}
    >
      <form className="settings-modal__card settings-modal__card--neutral" onSubmit={onSubmit}>
        <div className="settings-modal__header">
          <div>
            <h2 className="settings-modal__title" id="notification-settings-title">
              <span className="settings-modal__title-icon" aria-hidden="true">
                <BellIcon />
              </span>
              <span>Notifications</span>
            </h2>
            <p className="settings-modal__subtitle">Choose how Pickup Lane keeps you updated.</p>
          </div>
        </div>

        <label className="settings-toggle-row">
          <span>
            <strong>Email notifications</strong>
            <small>Game updates, booking changes, and account messages.</small>
          </span>
          <input
            checked={emailNotificationsEnabled}
            onChange={(event) => onEmailNotificationsChange(event.target.checked)}
            type="checkbox"
          />
        </label>

        {notificationError && <p className="profile-edit-error">{notificationError}</p>}

        <div className="settings-modal__actions">
          <button
            className="profile-edit-cancel"
            disabled={notificationStatus === 'saving'}
            onClick={handleCancel}
            type="button"
          >
            Back
          </button>
          <button
            className="profile-primary-action"
            disabled={notificationStatus === 'saving'}
            type="submit"
          >
            {notificationStatus === 'saving' ? 'Saving...' : 'Save'}
          </button>
        </div>
      </form>
    </div>
  )
}

export function AddPasswordModal({
  confirmPassword,
  newPassword,
  onClose,
  onConfirmPasswordChange,
  onNewPasswordChange,
  onSubmit,
  onToggleVisibility,
  passwordError,
  passwordStatus,
  passwordSuccess,
  showNewPassword,
}) {
  const handleClose = () => {
    if (passwordStatus !== 'saving') {
      onClose()
    }
  }

  useDismissibleModal(handleClose)

  return (
    <div
      className="settings-modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby="add-password-title"
      onMouseDown={(event) => dismissOnBackdropMouseDown(event, handleClose)}
    >
      <form className="settings-modal__card settings-modal__card--neutral" onSubmit={onSubmit}>
        <div className="settings-modal__header">
          <div>
            <h2 className="settings-modal__title" id="add-password-title">
              <span className="settings-modal__title-icon" aria-hidden="true">
                <KeyIcon />
              </span>
              <span>Add password</span>
            </h2>
            <p className="settings-modal__subtitle">Keep Google sign-in and add email/password sign-in for this account.</p>
          </div>
        </div>

        <PasswordField
          label="New password"
          onChange={onNewPasswordChange}
          onToggleVisibility={onToggleVisibility}
          showPassword={showNewPassword}
          value={newPassword}
        />
        <PasswordField
          label="Confirm password"
          onChange={onConfirmPasswordChange}
          onToggleVisibility={onToggleVisibility}
          showPassword={showNewPassword}
          value={confirmPassword}
        />

        <p className="settings-modal__note">
          Password must be at least 8 characters and include a number or symbol.
        </p>

        {passwordSuccess && <p className="settings-modal__success">{passwordSuccess}</p>}
        {passwordError && <p className="profile-edit-error">{passwordError}</p>}

        <div className="settings-modal__actions">
          <button
            className="profile-edit-cancel"
            disabled={passwordStatus === 'saving'}
            onClick={handleClose}
            type="button"
          >
            Close
          </button>
          <button
            className="profile-primary-action"
            disabled={passwordStatus === 'saving' || Boolean(passwordSuccess)}
            type="submit"
          >
            {passwordStatus === 'saving' ? 'Adding...' : 'Add password'}
          </button>
        </div>
      </form>
    </div>
  )
}
