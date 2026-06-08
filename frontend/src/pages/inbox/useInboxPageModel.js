import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth.js'
import { isAppNotification, isGameActivityNotification } from './inboxData.js'
import { loadInboxData, saveNotificationRead } from './inboxApi.js'
import { getFilteredSections, getInboxSections } from './inboxSelectors.js'

export function useInboxPageModel() {
  const navigate = useNavigate()
  const { appUser, currentUser: firebaseUser, isLoading } = useAuth()
  const [activeFilter, setActiveFilter] = useState('app')
  const [notifications, setNotifications] = useState([])
  const [activeNotification, setActiveNotification] = useState(null)
  const [sourceFilters, setSourceFilters] = useState({ app: 'all', game: 'all' })
  const [status, setStatus] = useState('loading')
  const [error, setError] = useState('')

  useEffect(() => {
    let ignore = false

    async function loadPageData() {
      setStatus('loading')
      setError('')

      try {
        if (isLoading) {
          return
        }

        if (!appUser?.id || !firebaseUser) {
          throw new Error('Sign in to view your inbox.')
        }

        const pageData = await loadInboxData(firebaseUser)

        if (!ignore) {
          setNotifications(pageData.notifications)
          setStatus('success')
        }
      } catch (requestError) {
        if (!ignore) {
          setError(
            requestError instanceof Error ? requestError.message : 'Unable to load inbox.',
          )
          setStatus('error')
        }
      }
    }

    loadPageData()

    return () => {
      ignore = true
    }
  }, [appUser?.id, firebaseUser, isLoading])

  const appNotifications = notifications.filter(isAppNotification)
  const gameNotifications = notifications.filter(isGameActivityNotification)
  const inboxSections = getInboxSections(appNotifications, gameNotifications, sourceFilters)
  const filteredSections = getFilteredSections(
    activeFilter,
    appNotifications,
    gameNotifications,
    sourceFilters,
  )

  function handleSourceFilterChange(sectionKey, sourceFilter) {
    setSourceFilters((currentFilters) => ({
      ...currentFilters,
      [sectionKey]: sourceFilter,
    }))
  }

  async function handleOpenNotification(notification) {
    const markedNotification = await markNotificationRead(notification)
    setActiveNotification(markedNotification)
  }

  function handleNotificationAction(action) {
    if (!action?.path) {
      return
    }

    setActiveNotification(null)
    navigate(action.path, action.state ? { state: action.state } : undefined)
  }

  async function markNotificationRead(notification) {
    if (notification.is_read) {
      return notification
    }

    const optimisticNotification = {
      ...notification,
      is_read: true,
      read_at: new Date().toISOString(),
    }

    setNotifications((currentNotifications) =>
      currentNotifications.map((currentNotification) =>
        currentNotification.id === notification.id ? optimisticNotification : currentNotification,
      ),
    )

    try {
      return await saveNotificationRead(firebaseUser, notification.id)
    } catch {
      setNotifications((currentNotifications) =>
        currentNotifications.map((currentNotification) =>
          currentNotification.id === notification.id ? notification : currentNotification,
        ),
      )
      return notification
    }
  }

  return {
    activeFilter,
    activeNotification,
    error,
    filteredSections,
    handleNotificationAction,
    handleOpenNotification,
    handleSourceFilterChange,
    inboxSections,
    setActiveFilter,
    setActiveNotification,
    status,
  }
}
