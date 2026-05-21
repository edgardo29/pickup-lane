import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth.js'
import { GAME_ACTIVITY_TYPES } from './inboxData.js'
import { loadInboxData, saveNotificationRead } from './inboxApi.js'
import { getFilteredSections } from './inboxSelectors.js'

export function useInboxPageModel() {
  const navigate = useNavigate()
  const { appUser, isLoading } = useAuth()
  const [activeFilter, setActiveFilter] = useState('app')
  const [games, setGames] = useState([])
  const [notifications, setNotifications] = useState([])
  const [activeNotification, setActiveNotification] = useState(null)
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

        if (!appUser?.id) {
          throw new Error('Sign in to view your inbox.')
        }

        const pageData = await loadInboxData(appUser.id)

        if (!ignore) {
          setNotifications(pageData.notifications)
          setGames(pageData.games)
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
  }, [appUser, isLoading])

  const gamesById = useMemo(() => new Map(games.map((game) => [game.id, game])), [games])
  const appNotifications = notifications.filter(
    (notification) => !GAME_ACTIVITY_TYPES.has(notification.notification_type),
  )
  const gameNotifications = notifications.filter((notification) =>
    GAME_ACTIVITY_TYPES.has(notification.notification_type),
  )
  const filteredSections = getFilteredSections(activeFilter, appNotifications, gameNotifications)
  const hasNoMatchingUpdates =
    status === 'success' &&
    notifications.length > 0 &&
    filteredSections.every((section) => section.items.length === 0)

  async function handleOpenNotification(notification) {
    const markedNotification = await markNotificationRead(notification)

    if (GAME_ACTIVITY_TYPES.has(notification.notification_type)) {
      if (notification.related_game_id) {
        navigate(`/games/${notification.related_game_id}`)
      }
      return
    }

    setActiveNotification(markedNotification)
  }

  function handleViewGame(gameId) {
    setActiveNotification(null)
    navigate(`/games/${gameId}`)
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
      return await saveNotificationRead(notification.id)
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
    gamesById,
    handleOpenNotification,
    handleViewGame,
    hasNoMatchingUpdates,
    notifications,
    setActiveFilter,
    setActiveNotification,
    status,
  }
}
