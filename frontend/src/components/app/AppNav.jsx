import { Link, NavLink, useLocation } from 'react-router-dom'
import { useEffect, useState } from 'react'
import logoNav from '../../assets/logo-nav.png'
import { useAuth } from '../../hooks/useAuth.js'
import { apiRequest } from '../../lib/apiClient.js'

const navItems = [
  { label: 'How it Works', href: '/#how-it-works', auth: 'public-only' },
  { label: 'Browse Games', to: '/games', auth: 'public' },
  { label: 'My Games', to: '/my-games', auth: 'private' },
  { label: 'Create Game', to: '/create-game', auth: 'private' },
  { label: 'Need a Sub', to: '/need-a-sub', auth: 'private' },
  { label: 'Inbox', to: '/inbox', auth: 'private' },
  { label: 'Profile', to: '/profile', auth: 'private' },
]

function AppNav({ isLoading: isForcedLoading = false, preferPublicWhileLoading = false }) {
  const { appUser, currentUser, isLoading: isAuthLoading } = useAuth()
  const location = useLocation()
  const isLoading = (isForcedLoading || isAuthLoading) && !preferPublicWhileLoading
  const [unreadCount, setUnreadCount] = useState(0)
  const [isMenuOpen, setIsMenuOpen] = useState(false)

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

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      setIsMenuOpen(false)
    }, 0)

    return () => window.clearTimeout(timeoutId)
  }, [location.pathname])

  useEffect(() => {
    function closeOnEscape(event) {
      if (event.key === 'Escape') {
        setIsMenuOpen(false)
      }
    }

    window.addEventListener('keydown', closeOnEscape)

    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [])

  const displayName = appUser ? getDisplayName(appUser, currentUser) : 'Sign In / Register'
  const initials = getInitials(appUser, currentUser)
  const visibleNavItems = navItems.filter((item) => {
    if (item.auth === 'public') {
      return true
    }

    if (item.auth === 'public-only') {
      return !appUser
    }

    return Boolean(appUser)
  })

  function closeMenu() {
    setIsMenuOpen(false)
  }

  return (
    <header className="app-nav">
      <NavLink className="app-nav__brand" to="/" aria-label="Pickup Lane home">
        <span className="app-nav__brand-logo" aria-hidden="true">
          <img src={logoNav} alt="" />
        </span>
        <span className="app-nav__brand-wordmark">
          PICKUP <strong>LANE</strong>
        </span>
      </NavLink>

      <nav
        className={`app-nav__links ${isMenuOpen ? 'app-nav__links--open' : ''}`}
        aria-label="Main navigation"
      >
        {!isLoading && (
          <Link
            className={`app-nav__menu-user ${appUser ? '' : 'app-nav__menu-user--guest'}`}
            to={appUser ? '/profile' : '/sign-in'}
            onClick={closeMenu}
          >
            {appUser && <span>{initials}</span>}
            <strong>{displayName}</strong>
          </Link>
        )}

        {isLoading ? (
          <span className="app-nav__loading-text">Loading your account</span>
        ) : (
          visibleNavItems.map((item) =>
            item.href ? (
              <a className="app-nav__link" href={item.href} key={item.label} onClick={closeMenu}>
                {item.label}
              </a>
            ) : (
              <NavLink className="app-nav__link" to={item.to} key={item.label} onClick={closeMenu}>
                {item.label}
                {item.label === 'Inbox' && unreadCount > 0 && (
                  <span className="app-nav__badge">{unreadCount}</span>
                )}
              </NavLink>
            ),
          )
        )}
      </nav>

      <div className="app-nav__actions">
        {isLoading ? (
          <span className="app-nav__user app-nav__user--loading" aria-hidden="true">
            <span />
            <i />
          </span>
        ) : (
          <Link
            className={`app-nav__user ${appUser ? '' : 'app-nav__user--guest'}`}
            to={appUser ? '/profile' : '/sign-in'}
            onClick={closeMenu}
          >
            {appUser && <span>{initials}</span>}
            <strong>{displayName}</strong>
          </Link>
        )}
        {!isLoading && (
          <button
            className="app-nav__menu-button"
            type="button"
            aria-label={isMenuOpen ? 'Close navigation menu' : 'Open navigation menu'}
            aria-expanded={isMenuOpen}
            onClick={() => setIsMenuOpen((current) => !current)}
          >
            <span />
            <span />
            <span />
          </button>
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

export default AppNav
