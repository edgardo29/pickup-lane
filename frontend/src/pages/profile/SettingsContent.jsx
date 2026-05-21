import { Link } from 'react-router-dom'
import { AppPageHeader } from '../../components/app/index.js'
import {
  AddPasswordModal,
  DeleteAccountModal,
  NotificationSettingsModal,
} from './SettingsModals.jsx'
import { SettingsGroup } from './SettingsGroup.jsx'
import { ProfileShell } from './ProfileShell.jsx'

function SettingsContent({
  accountAccessRows,
  accountDetailRows,
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
}) {
  return (
    <ProfileShell>
      <section className="settings-layout">
        <div className="settings-main">
          <div className="profile-subpage-heading">
            <Link className="settings-header-back" to="/profile">
              Back to profile
            </Link>
            <AppPageHeader
              title="Settings"
              subtitle="Update account preferences and support options."
            />
          </div>

          <SettingsGroup title="Account Details" rows={accountDetailRows} />
          <SettingsGroup title="Preferences & Account" rows={preferenceRows} />
          {accountAccessRows.length > 0 && (
            <SettingsGroup title="Account Access" rows={accountAccessRows} />
          )}
          <SettingsGroup title="Account" rows={accountRows} />
        </div>
      </section>

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
    </ProfileShell>
  )
}

export default SettingsContent
