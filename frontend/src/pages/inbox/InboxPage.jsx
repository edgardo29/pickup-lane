import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AppPageHeader, AppPageShell, AppTabs } from '../../components/app/index.js'
import { ChatIcon } from '../../components/BrowseIcons.jsx'
import { useAuth } from '../../hooks/useAuth.js'
import { apiRequest } from '../../lib/apiClient.js'
import '../../styles/inbox.css'
import InboxSection from './InboxSection.jsx'
import NotificationModal from './NotificationModal.jsx'
import { GAME_ACTIVITY_TYPES, getFilteredSections, inboxTabs } from './inboxData.js'

function InboxPage() {
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

    async function loadInbox() {
      setStatus('loading')
      setError('')

      try {
        if (isLoading) {
          return
        }

        if (!appUser?.id) {
          throw new Error('Sign in to view your inbox.')
        }

        const [notificationsResponse, gamesResponse] = await Promise.all([
          apiRequest(`/notifications?user_id=${appUser.id}`),
          apiRequest('/games'),
        ])

        if (!ignore) {
          setNotifications(notificationsResponse)
          setGames(gamesResponse)
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

    loadInbox()

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

  return (
    <AppPageShell className="inbox-page" mainClassName="app-page-shell--narrow inbox-shell">
      <AppPageHeader
        title="Inbox"
        subtitle="Review notifications and game activity."
        tabs={
          <AppTabs
            ariaLabel="Inbox filters"
            items={inboxTabs}
            onChange={setActiveFilter}
            value={activeFilter}
          />
        }
      />

      {status === 'loading' && <InboxState title="Loading inbox" />}
      {status === 'error' && <InboxState title="Could not load inbox" message={error} />}

      {status === 'success' && notifications.length === 0 && (
        <InboxState title="Nothing here yet" message="Your updates will show up here." />
      )}

      {status === 'success' && notifications.length > 0 && (
        <div className="inbox-section-stack">
          {filteredSections.map((section) => (
            <InboxSection
              gamesById={gamesById}
              items={section.items}
              key={section.title}
              onOpenNotification={handleOpenNotification}
              section={section}
            />
          ))}
        </div>
      )}

      {status === 'success' &&
        notifications.length > 0 &&
        filteredSections.every((section) => section.items.length === 0) && (
          <InboxState title="No matching updates" message="Try another inbox filter." />
        )}

      {activeNotification && (
        <NotificationModal
          game={gamesById.get(activeNotification.related_game_id)}
          notification={activeNotification}
          onClose={() => setActiveNotification(null)}
          onViewGame={(gameId) => {
            setActiveNotification(null)
            navigate(`/games/${gameId}`)
          }}
        />
      )}
    </AppPageShell>
  )

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
      return await apiRequest(`/notifications/${notification.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_read: true }),
      })
    } catch {
      setNotifications((currentNotifications) =>
        currentNotifications.map((currentNotification) =>
          currentNotification.id === notification.id ? notification : currentNotification,
        ),
      )
      return notification
    }
  }
}

function InboxState({ title, message }) {
  return (
    <section className="inbox-state">
      <ChatIcon />
      <h2>{title}</h2>
      {message && <p>{message}</p>}
    </section>
  )
}

export default InboxPage
