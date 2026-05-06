import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import BrowseAppNav from '../components/BrowseAppNav.jsx'
import { ChatIcon } from '../components/BrowseIcons.jsx'
import { apiRequest } from '../lib/apiClient.js'
import '../styles/inbox.css'

const DEMO_CURRENT_USER_AUTH_ID = 'demo-current-user'
const GAME_ACTIVITY_TYPES = new Set(['chat_message'])
const FILTERS = [
  { key: 'app', label: 'App Notifications' },
  { key: 'game', label: 'Game Activity' },
]

function InboxPage() {
  const navigate = useNavigate()
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
        const usersResponse = await apiRequest('/users')
        const demoUser = usersResponse.find((user) => user.auth_user_id === DEMO_CURRENT_USER_AUTH_ID)

        if (!demoUser) {
          throw new Error('Demo signed-in user was not found. Rerun the demo seed.')
        }

        const [notificationsResponse, gamesResponse] = await Promise.all([
          apiRequest(`/notifications?user_id=${demoUser.id}`),
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
  }, [])

  const gamesById = useMemo(() => new Map(games.map((game) => [game.id, game])), [games])
  const appNotifications = notifications.filter(
    (notification) => !GAME_ACTIVITY_TYPES.has(notification.notification_type),
  )
  const gameNotifications = notifications.filter((notification) =>
    GAME_ACTIVITY_TYPES.has(notification.notification_type),
  )
  const filteredSections = getFilteredSections(activeFilter, appNotifications, gameNotifications)

  return (
    <div className="inbox-page">
      <BrowseAppNav />

      <main className="inbox-shell">
        <section className="inbox-heading">
          <div>
            <h1>Inbox</h1>
            <p>Messages and updates for you.</p>
          </div>
        </section>

        <div className="inbox-filter-row" role="tablist" aria-label="Inbox filters">
          {FILTERS.map((filter) => (
            <button
              className={activeFilter === filter.key ? 'active' : ''}
              type="button"
              role="tab"
              aria-selected={activeFilter === filter.key}
              key={filter.key}
              onClick={() => setActiveFilter(filter.key)}
            >
              {filter.label}
            </button>
          ))}
        </div>

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
      </main>
    </div>
  )

  async function handleOpenNotification(notification) {
    await markNotificationRead(notification)

    if (GAME_ACTIVITY_TYPES.has(notification.notification_type)) {
      if (notification.related_game_id) {
        navigate(`/games/${notification.related_game_id}`)
      }
      return
    }

    setActiveNotification({ ...notification, is_read: true })
  }

  async function markNotificationRead(notification) {
    if (notification.is_read) {
      return
    }

    setNotifications((currentNotifications) =>
      currentNotifications.map((currentNotification) =>
        currentNotification.id === notification.id
          ? { ...currentNotification, is_read: true, read_at: new Date().toISOString() }
          : currentNotification,
      ),
    )

    await apiRequest(`/notifications/${notification.id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ is_read: true }),
    }).catch(() => {})
  }
}

function InboxSection({ gamesById, items, onOpenNotification, section }) {
  if (items.length === 0) {
    return null
  }

  return (
    <section className="inbox-section">
      <div className="inbox-section__heading">
        {section.icon}
        <div>
          <h2>{section.title}</h2>
          <p>{section.description}</p>
        </div>
      </div>

      <div className="inbox-list">
        {items.map((notification) => (
          <InboxRow
            game={gamesById.get(notification.related_game_id)}
            key={notification.id}
            notification={notification}
            onOpenNotification={onOpenNotification}
          />
        ))}
      </div>
    </section>
  )
}

function InboxRow({ game, notification, onOpenNotification }) {
  const isGameActivity = GAME_ACTIVITY_TYPES.has(notification.notification_type)
  const title = isGameActivity && game ? game.title : notification.title
  const body = isGameActivity ? 'New activity in game chat.' : notification.body

  return (
    <button
      className={`inbox-row ${notification.is_read ? '' : 'inbox-row--unread'}`}
      type="button"
      onClick={() => onOpenNotification(notification)}
    >
      <span className="inbox-row__body">
        <span className="inbox-row__titleline">
          <strong>{title}</strong>
          {!notification.is_read && <em>New</em>}
        </span>
        <span>{body}</span>
      </span>

      <span className="inbox-row__meta">
        {formatRelativeTime(notification.created_at)}
        <i aria-hidden="true" />
      </span>
    </button>
  )
}

function NotificationModal({ game, notification, onClose, onViewGame }) {
  return (
    <div className="inbox-modal-backdrop" role="presentation" onClick={onClose}>
      <section
        className="inbox-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="inbox-modal-title"
        onClick={(event) => event.stopPropagation()}
      >
        <button className="inbox-modal__close" type="button" onClick={onClose} aria-label="Close">
          ×
        </button>

        <p className="inbox-modal__meta">{formatFullDate(notification.created_at)}</p>
        <h2 id="inbox-modal-title">{notification.title}</h2>
        <p>{notification.body}</p>

        {game && (
          <button
            className="inbox-modal__action"
            type="button"
            onClick={() => onViewGame(game.id)}
          >
            View game
          </button>
        )}
      </section>
    </div>
  )
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

function getFilteredSections(activeFilter, appNotifications, gameNotifications) {
  const sections = [
    {
      description: 'Important updates and support messages.',
      icon: <MegaphoneIcon />,
      items: appNotifications,
      key: 'app',
      title: 'App Notifications',
    },
    {
      description: 'Game chat and activity from games you joined or host.',
      icon: <ChatIcon />,
      items: gameNotifications,
      key: 'game',
      title: 'Game Activity',
    },
  ]

  return sections.filter((section) => section.key === activeFilter)
}

function formatRelativeTime(value) {
  const deltaMs = Date.now() - new Date(value).getTime()
  const minute = 60 * 1000
  const hour = 60 * minute
  const day = 24 * hour

  if (deltaMs < hour) {
    return `${Math.max(1, Math.round(deltaMs / minute))}m`
  }

  if (deltaMs < day) {
    return `${Math.round(deltaMs / hour)}h`
  }

  return `${Math.round(deltaMs / day)}d`
}

function formatFullDate(value) {
  return new Intl.DateTimeFormat('en-US', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

function MegaphoneIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4 13.5h3.4l9.1 4.3V5.2L7.4 9.5H4Z" />
      <path d="M7.4 13.5 8.7 20H11" />
      <path d="M19 9.2c1 .7 1.5 1.6 1.5 2.8s-.5 2.1-1.5 2.8" />
    </svg>
  )
}

export default InboxPage
