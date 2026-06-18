import { useState } from 'react'
import { saveUserSettings } from './profileApi.js'

export function useNotificationSettings({
  effectiveSettings,
  firebaseUser,
  setSettingsOverride,
}) {
  const [isNotificationOpen, setIsNotificationOpen] = useState(false)
  const [emailNotificationsEnabled, setEmailNotificationsEnabled] = useState(false)
  const [notificationStatus, setNotificationStatus] = useState('idle')
  const [notificationError, setNotificationError] = useState('')

  function openNotificationModal() {
    setNotificationError('')
    setNotificationStatus('idle')
    setEmailNotificationsEnabled(Boolean(effectiveSettings.email_notifications_enabled))
    setIsNotificationOpen(true)
  }

  const handleSaveNotifications = async (event) => {
    event.preventDefault()
    setNotificationStatus('saving')
    setNotificationError('')

    try {
      const savedSettings = await saveUserSettings(firebaseUser, {
        email_notifications_enabled: emailNotificationsEnabled,
      })

      setSettingsOverride(
        savedSettings || {
          email_notifications_enabled: emailNotificationsEnabled,
        },
      )
      setNotificationStatus('idle')
      setIsNotificationOpen(false)
    } catch (requestError) {
      setNotificationError(
        requestError instanceof Error ? requestError.message : 'Unable to save notifications.',
      )
      setNotificationStatus('idle')
    }
  }

  return {
    emailNotificationsEnabled,
    handleSaveNotifications,
    isNotificationOpen,
    notificationError,
    notificationStatus,
    openNotificationModal,
    setEmailNotificationsEnabled,
    setIsNotificationOpen,
  }
}
