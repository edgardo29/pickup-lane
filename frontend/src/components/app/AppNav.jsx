import { AppNavActions } from './AppNavActions.jsx'
import { AppNavBrand } from './AppNavBrand.jsx'
import { AppNavLinks } from './AppNavLinks.jsx'
import { useAppNavState } from './useAppNavState.js'

function AppNav({ isLoading: isForcedLoading = false, preferPublicWhileLoading = false }) {
  const navState = useAppNavState({ isForcedLoading, preferPublicWhileLoading })

  return (
    <header className="app-nav">
      <AppNavBrand />

      <AppNavLinks
        appUser={navState.appUser}
        closeMenu={navState.closeMenu}
        displayName={navState.displayName}
        hasAdminWorkspaceAccess={navState.hasAdminWorkspaceAccess}
        initials={navState.initials}
        isLoading={navState.isLoading}
        isMenuOpen={navState.isMenuOpen}
        unreadCount={navState.unreadCount}
        visibleAdminNavItems={navState.visibleAdminNavItems}
        visibleNavItems={navState.visibleNavItems}
      />

      <AppNavActions
        adminEntryPath={navState.adminEntryPath}
        appUser={navState.appUser}
        closeMenu={navState.closeMenu}
        displayName={navState.displayName}
        hasAdminWorkspaceAccess={navState.hasAdminWorkspaceAccess}
        initials={navState.initials}
        isLoading={navState.isLoading}
        isMenuOpen={navState.isMenuOpen}
        toggleMenu={navState.toggleMenu}
      />
    </header>
  )
}

export default AppNav
