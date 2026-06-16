import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth.js'
import { appNavItems } from './appNavData.js'
import { fetchUnreadNotificationCount } from './appNavApi.js'
import { getDisplayName, getInitials } from './appNavFormatters.js'

const DESKTOP_NAV_MEDIA_QUERY = '(min-width: 1181px)'

export function useAppNavState({
  isForcedLoading = false,
  preferPublicWhileLoading = false,
}) {
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
        const nextUnreadCount = await fetchUnreadNotificationCount(currentUser)

        if (!ignore) {
          setUnreadCount(nextUnreadCount)
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
  }, [appUser?.id, currentUser])

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

  useEffect(() => {
    const desktopQuery = window.matchMedia(DESKTOP_NAV_MEDIA_QUERY)

    function closeOnDesktop(event) {
      if (event.matches) {
        setIsMenuOpen(false)
      }
    }

    closeOnDesktop(desktopQuery)
    desktopQuery.addEventListener('change', closeOnDesktop)

    return () => desktopQuery.removeEventListener('change', closeOnDesktop)
  }, [])

  const displayName = appUser ? getDisplayName(appUser, currentUser) : 'Sign In / Register'
  const initials = getInitials(appUser, currentUser)
  const visibleNavItems = appNavItems.filter((item) => {
    if (item.auth === 'public') {
      return true
    }

    if (item.auth === 'public-only') {
      return !appUser
    }

    if (item.auth === 'admin') {
      return appUser?.role === 'admin'
    }

    return Boolean(appUser)
  })

  function closeMenu() {
    setIsMenuOpen(false)
  }

  function toggleMenu() {
    setIsMenuOpen((current) => !current)
  }

  return {
    appUser,
    closeMenu,
    displayName,
    initials,
    isLoading,
    isMenuOpen,
    toggleMenu,
    unreadCount,
    visibleNavItems,
  }
}
