import {
  AddPasswordModal,
  DeleteAccountModal,
  NotificationSettingsModal,
} from './SettingsModals.jsx'
import { SettingsRow } from './SettingsGroup.jsx'
import { ControlsIcon } from './ProfileIcons.jsx'

function SettingsContent({
  accountAccessRows,
  accountRows,
  confirmPassword,
  deleteConfirmation,
  deleteError,
  deleteStatus,
  emailNotificationsEnabled,
  handleAddPassword,
  handleDeleteAccount,
  handleSaveNotifications,
  isDeleteOpen,
  isNotificationOpen,
  isPasswordOpen,
  newPassword,
  notificationError,
  notificationStatus,
  passwordError,
  passwordStatus,
  passwordSuccess,
  preferenceRows,
  setConfirmPassword,
  setDeleteConfirmation,
  setEmailNotificationsEnabled,
  setIsDeleteOpen,
  setIsNotificationOpen,
  setIsPasswordOpen,
  setNewPassword,
  setShowNewPassword,
  showNewPassword,
  supportRows,
}) {
  const logOutRow = accountRows.find((row) => row.title === 'Log Out')
  const deleteAccountRow = accountRows.find((row) => row.title === 'Delete Account')
  const settingsRows = [
    preferenceRows[0],
    preferenceRows[1],
    ...accountAccessRows,
    supportRows[0],
    supportRows[1],
    supportRows[2],
    logOutRow,
  ].filter(Boolean)

  return (
    <>
      <section className="profile-settings-section profile-settings-section--manage" id="profile-settings" aria-labelledby="profile-settings-title">
        <div className="profile-manage-heading">
          <span className="profile-manage-heading__icon">
            <ControlsIcon />
          </span>
          <div>
            <h2 id="profile-settings-title">Manage</h2>
            <p>Manage your preferences and account settings.</p>
          </div>
        </div>
        <div className="profile-settings-grid">
          {settingsRows.map((row) => (
            <SettingsRow key={row.title} row={row} />
          ))}
        </div>
      </section>

      {deleteAccountRow && (
        <section className="profile-danger-section" aria-label="Danger zone">
          <SettingsRow row={deleteAccountRow} />
        </section>
      )}

      {isDeleteOpen && (
        <DeleteAccountModal
          deleteConfirmation={deleteConfirmation}
          deleteError={deleteError}
          deleteStatus={deleteStatus}
          onCancel={() => setIsDeleteOpen(false)}
          onConfirmationChange={setDeleteConfirmation}
          onSubmit={handleDeleteAccount}
        />
      )}

      {isNotificationOpen && (
        <NotificationSettingsModal
          emailNotificationsEnabled={emailNotificationsEnabled}
          notificationError={notificationError}
          notificationStatus={notificationStatus}
          onCancel={() => setIsNotificationOpen(false)}
          onEmailNotificationsChange={setEmailNotificationsEnabled}
          onSubmit={handleSaveNotifications}
        />
      )}

      {isPasswordOpen && (
        <AddPasswordModal
          confirmPassword={confirmPassword}
          newPassword={newPassword}
          onClose={() => setIsPasswordOpen(false)}
          onConfirmPasswordChange={setConfirmPassword}
          onNewPasswordChange={setNewPassword}
          onSubmit={handleAddPassword}
          onToggleVisibility={() => setShowNewPassword((current) => !current)}
          passwordError={passwordError}
          passwordStatus={passwordStatus}
          passwordSuccess={passwordSuccess}
          showNewPassword={showNewPassword}
        />
      )}
    </>
  )
}

export default SettingsContent
