import { Link, NavLink, useLocation } from 'react-router-dom'
import { isAdminWorkspaceItemActive } from '../../pages/admin/shared/adminWorkspaceData.js'

function AppNavMenuSection({
  closeMenu,
  items,
  label,
  menuOnly = false,
  pathname,
  unreadCount,
}) {
  function isMenuItemActive(item, isActive) {
    return isAdminWorkspaceItemActive(item, pathname) || isActive
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
  hasAdminWorkspaceAccess,
  initials,
  isLoading,
  isMenuOpen,
  unreadCount,
  visibleAdminNavItems,
  visibleNavItems,
}) {
  const { pathname } = useLocation()
  const appSection = (
    <AppNavMenuSection
      closeMenu={closeMenu}
      items={visibleNavItems}
      label={hasAdminWorkspaceAccess ? 'App' : ''}
      pathname={pathname}
      unreadCount={unreadCount}
    />
  )
  const adminSection = hasAdminWorkspaceAccess ? (
    <AppNavMenuSection
      closeMenu={closeMenu}
      items={visibleAdminNavItems}
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
      ) : (
        <>
          {appSection}
          {adminSection}
        </>
      )}
    </nav>
  )
}
