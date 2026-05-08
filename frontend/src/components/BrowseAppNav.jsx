import { Link, NavLink } from 'react-router-dom'
import { useEffect, useState } from 'react'
import logo from '../assets/logo.png'
import { useAuth } from '../hooks/useAuth.js'
import { apiRequest } from '../lib/apiClient.js'

const navItems = [
  { label: 'Browse Games', to: '/games', auth: 'public' },
  { label: 'My Games', to: '/my-games', auth: 'private' },
  { label: 'Create Game', to: '/create-game', auth: 'private' },
  { label: 'Player Hub', to: '/player-hub', auth: 'private' },
  { label: 'Inbox', to: '/inbox', auth: 'private' },
  { label: 'Profile', to: '/profile', auth: 'private' },
]

function BrowseAppNav({ isLoading: isForcedLoading = false }) {
  const { appUser, currentUser, isLoading: isAuthLoading } = useAuth()
  const isLoading = isForcedLoading || isAuthLoading
  const [unreadCount, setUnreadCount] = useState(0)

  useEffect(() => {
    let ignore = false

    async function loadUnreadCount() {
      if (!appUser?.id) {
        setUnreadCount(0)
        return
      }

      try {
        const unreadNotifications = await apiRequest(
          `/notifications?user_id=${appUser.id}&is_read=false`,
        )

        if (!ignore) {
          setUnreadCount(unreadNotifications.length)
        }
      } catch {
        if (!ignore) {
          setUnreadCount(0)
        }
      }
    }

    loadUnreadCount()

    return () => {
      ignore = true
    }
  }, [appUser?.id])

  const displayName = appUser ? getDisplayName(appUser, currentUser) : 'Sign In'
  const initials = getInitials(appUser, currentUser)
  const visibleNavItems = navItems.filter(
    (item) => item.auth === 'public' || Boolean(appUser),
  )

  return (
    <header className="browse-nav">
      <NavLink className="browse-nav__brand" to="/" aria-label="Pickup Lane home">
        <img src={logo} alt="" />
        <span>
          PICKUP <strong>LANE</strong>
        </span>
      </NavLink>

      <nav className="browse-nav__links" aria-label="Public navigation">
        {isLoading
          ? <span className="browse-nav__loading-text">Loading your account</span>
          : visibleNavItems.map((item) => (
              <NavLink className="browse-nav__link" to={item.to} key={item.label}>
                {item.label}
                {item.label === 'Inbox' && unreadCount > 0 && (
                  <span className="browse-nav__badge">{unreadCount}</span>
                )}
              </NavLink>
            ))}
      </nav>

      <div className="browse-nav__actions">
        {isLoading ? (
          <span className="browse-nav__user browse-nav__user--loading" aria-hidden="true">
            <span />
            <i />
          </span>
        ) : (
          <Link
            className="browse-nav__user"
            to={appUser ? '/profile' : '/sign-in'}
            aria-label={appUser ? 'Open profile' : 'Sign in'}
          >
            {appUser && <span>{initials}</span>}
            {displayName}
          </Link>
        )}
      </div>
    </header>
  )
}

function getDisplayName(appUser, firebaseUser) {
  const fullName = `${appUser?.first_name || ''} ${appUser?.last_name || ''}`.trim()

  if (fullName) {
    return fullName
  }

  return appUser?.email || firebaseUser?.email || 'Sign In'
}

function getInitials(appUser, firebaseUser) {
  const first = appUser?.first_name?.[0]
  const last = appUser?.last_name?.[0]

  if (first || last) {
    return `${first || ''}${last || ''}`.toUpperCase()
  }

  return (appUser?.email || firebaseUser?.email || 'PL').slice(0, 2).toUpperCase()
}

export default BrowseAppNav
