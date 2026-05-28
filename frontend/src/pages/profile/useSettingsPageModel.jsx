import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth.js'
import { getNotificationSummary } from './profileFormatters.js'
import { buildSettingsRows } from './settingsRows.jsx'
import { useAddPasswordSettings } from './useAddPasswordSettings.js'
import { useDeleteAccountSettings } from './useDeleteAccountSettings.js'
import { useNotificationSettings } from './useNotificationSettings.js'
import { useProfileContext } from './useProfileContext.js'

export function useSettingsPageModel() {
  const navigate = useNavigate()
  const {
    addPasswordToCurrentAccount,
    currentUser: authUser,
    deleteAccount,
    logout,
  } = useAuth()
  const {
    currentUser,
    gameCreditBalance,
    paymentMethods,
    settings,
    stats,
    status,
    error,
  } = useProfileContext()
  const [currentUserOverride, setCurrentUserOverride] = useState(null)
  const [settingsOverride, setSettingsOverride] = useState(null)
  const effectiveCurrentUser = useMemo(
    () => (currentUser ? { ...currentUser, ...(currentUserOverride || {}) } : currentUser),
    [currentUser, currentUserOverride],
  )
  const effectiveSettings = useMemo(
    () => ({ ...settings, ...(settingsOverride || {}) }),
    [settings, settingsOverride],
  )
  const deleteSettings = useDeleteAccountSettings({ deleteAccount, logout, navigate })
  const notificationSettings = useNotificationSettings({
    currentUser,
    effectiveSettings,
    setSettingsOverride,
  })
  const passwordSettings = useAddPasswordSettings({ addPasswordToCurrentAccount })
  const defaultPaymentMethod =
    paymentMethods.find((method) => method.is_default) || paymentMethods[0] || null
  const providerIds = authUser?.providerData?.map((provider) => provider.providerId) ?? []
  const canAddPassword =
    Boolean(authUser?.email) &&
    providerIds.includes('google.com') &&
    !providerIds.includes('password')
  const rows = buildSettingsRows({
    canAddPassword,
    defaultPaymentMethod,
    logout,
    navigate,
    notificationSummary: getNotificationSummary(effectiveSettings),
    onOpenDelete: deleteSettings.openDeleteModal,
    onOpenNotifications: notificationSettings.openNotificationModal,
    onOpenPassword: passwordSettings.openPasswordModal,
  })

  const handleProfileSaved = ({ currentUser: savedUser, settings: savedSettings }) => {
    if (savedUser) {
      setCurrentUserOverride(savedUser)
    }
    if (savedSettings) {
      setSettingsOverride(savedSettings)
    }
  }

  return {
    ...rows,
    confirmPassword: passwordSettings.confirmPassword,
    currentUser: effectiveCurrentUser,
    deleteConfirmation: deleteSettings.deleteConfirmation,
    deleteError: deleteSettings.deleteError,
    deleteStatus: deleteSettings.deleteStatus,
    emailNotificationsEnabled: notificationSettings.emailNotificationsEnabled,
    error,
    gameCreditBalance,
    handleAddPassword: passwordSettings.handleAddPassword,
    handleDeleteAccount: deleteSettings.handleDeleteAccount,
    handleProfileSaved,
    handleSaveNotifications: notificationSettings.handleSaveNotifications,
    isDeleteOpen: deleteSettings.isDeleteOpen,
    isNotificationOpen: notificationSettings.isNotificationOpen,
    isPasswordOpen: passwordSettings.isPasswordOpen,
    newPassword: passwordSettings.newPassword,
    notificationError: notificationSettings.notificationError,
    notificationStatus: notificationSettings.notificationStatus,
    passwordError: passwordSettings.passwordError,
    passwordStatus: passwordSettings.passwordStatus,
    passwordSuccess: passwordSettings.passwordSuccess,
    setConfirmPassword: passwordSettings.setConfirmPassword,
    setDeleteConfirmation: deleteSettings.setDeleteConfirmation,
    setEmailNotificationsEnabled: notificationSettings.setEmailNotificationsEnabled,
    setIsDeleteOpen: deleteSettings.setIsDeleteOpen,
    setIsNotificationOpen: notificationSettings.setIsNotificationOpen,
    setIsPasswordOpen: passwordSettings.setIsPasswordOpen,
    setNewPassword: passwordSettings.setNewPassword,
    setShowNewPassword: passwordSettings.setShowNewPassword,
    showNewPassword: passwordSettings.showNewPassword,
    settings: effectiveSettings,
    status,
    stats,
  }
}
