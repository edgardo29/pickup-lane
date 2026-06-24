import { useEffect, useRef } from 'react'
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

function AppNavAdminGroups({ closeMenu, groups, pathname }) {
  return (
    <div className="app-nav__menu-section app-nav__menu-section--menu-only app-nav__menu-section--admin">
      <span className="app-nav__menu-section-title">Admin</span>
      <div className="app-nav__admin-groups">
        {groups.map((group) => {
          const Icon = group.icon

          return (
            <section className="app-nav__admin-group" key={group.id}>
              <span className="app-nav__admin-group-title">
                <Icon aria-hidden="true" />
                <span>{group.label}</span>
              </span>
              <div className="app-nav__admin-group-items">
                {group.items.map((item) => (
                  <NavLink
                    className={() => (
                      `app-nav__link app-nav__admin-item ${
                        isAdminWorkspaceItemActive(item, pathname) ? 'active' : ''
                      }`
                    )}
                    end={item.end}
                    key={item.to}
                    to={item.to}
                    onClick={closeMenu}
                  >
                    {item.label}
                  </NavLink>
                ))}
              </div>
            </section>
          )
        })}
      </div>
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
  visibleAdminNavGroups,
  visibleNavItems,
}) {
  const { pathname } = useLocation()
  const menuRef = useRef(null)

  useEffect(() => {
    if (!isMenuOpen) {
      return undefined
    }

    const frameId = window.requestAnimationFrame(() => {
      menuRef.current
        ?.querySelector('.app-nav__link.active')
        ?.scrollIntoView({ block: 'nearest' })
    })

    return () => window.cancelAnimationFrame(frameId)
  }, [isMenuOpen, pathname])

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
    <AppNavAdminGroups
      closeMenu={closeMenu}
      groups={visibleAdminNavGroups}
      pathname={pathname}
    />
  ) : null

  return (
    <nav
      className={`app-nav__links ${isMenuOpen ? 'app-nav__links--open' : ''}`}
      aria-label="Main navigation"
      ref={menuRef}
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
