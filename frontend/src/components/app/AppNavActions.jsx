import { Link, NavLink } from 'react-router-dom'
import { ShieldCheckIcon } from '../BrowseIcons.jsx'

export function AppNavActions({
  adminEntryPath,
  appUser,
  closeMenu,
  displayName,
  hasAdminWorkspaceAccess,
  initials,
  isLoading,
  isMenuOpen,
  toggleMenu,
}) {
  return (
    <div className="app-nav__actions">
      {!isLoading && appUser && hasAdminWorkspaceAccess && (
        <NavLink className="app-nav__admin-link" to={adminEntryPath} onClick={closeMenu}>
          <ShieldCheckIcon />
          Admin
        </NavLink>
      )}
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
          onClick={toggleMenu}
        >
          <span />
          <span />
          <span />
        </button>
      )}
    </div>
  )
}
