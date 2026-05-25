import { Link, NavLink, useLocation } from 'react-router-dom'
import { adminWorkspaceNavItems } from '../../pages/admin/shared/adminWorkspaceData.js'

function AppNavMenuSection({
  closeMenu,
  items,
  label,
  menuOnly = false,
  pathname,
  unreadCount,
}) {
  function isMenuItemActive(item, isActive) {
    if (item.to === '/admin/official-games') {
      return (
        pathname === item.to
        || (pathname.startsWith('/admin/official-games/') && pathname !== '/admin/official-games/new')
      )
    }

    return isActive
  }

  return (
    <div className={`app-nav__menu-section ${menuOnly ? 'app-nav__menu-section--menu-only' : ''}`}>
      {label && <span className="app-nav__menu-section-title">{label}</span>}
      {items.map((item) =>
        item.href ? (
          <a className="app-nav__link" href={item.href} key={item.label} onClick={closeMenu}>
            {item.label}
          </a>
        ) : (
          <NavLink
            className={({ isActive }) => (
              `app-nav__link ${isMenuItemActive(item, isActive) ? 'active' : ''}`
            )}
            end={item.end}
            key={item.label}
            to={item.to}
            onClick={closeMenu}
          >
            {item.label}
            {item.label === 'Inbox' && unreadCount > 0 && (
              <span className="app-nav__badge">{unreadCount}</span>
            )}
          </NavLink>
        ),
      )}
    </div>
  )
}

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
  const { pathname } = useLocation()
  const isAdmin = appUser?.role === 'admin'
  const isAdminRoute = pathname.startsWith('/admin')
  const appSection = (
    <AppNavMenuSection
      closeMenu={closeMenu}
      items={visibleNavItems}
      label={isAdmin ? 'App' : ''}
      pathname={pathname}
      unreadCount={unreadCount}
    />
  )
  const adminSection = isAdmin ? (
    <AppNavMenuSection
      closeMenu={closeMenu}
      items={adminWorkspaceNavItems}
      label="Admin"
      menuOnly
      pathname={pathname}
      unreadCount={0}
    />
  ) : null

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
      ) : isAdminRoute ? (
        <>
          {adminSection}
          {appSection}
        </>
      ) : (
        <>
          {appSection}
          {adminSection}
        </>
      )}
    </nav>
  )
}
