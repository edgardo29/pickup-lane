import { Link, NavLink } from 'react-router-dom'

export function AppNavLinks({
  appUser,
  closeMenu,
  displayName,
  initials,
  isLoading,
  isMenuOpen,
  unreadCount,
  visibleNavItems,
}) {
  return (
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
  )
}
