import { useEffect, useLayoutEffect } from 'react'
import { useLocation } from 'react-router-dom'

export function ScrollToTop() {
  const location = useLocation()

  useEffect(() => {
    if ('scrollRestoration' in window.history) {
      window.history.scrollRestoration = 'manual'
    }
  }, [])

  useLayoutEffect(() => {
    resetPageScroll()

    const firstFrame = window.requestAnimationFrame(() => {
      resetPageScroll()

      window.requestAnimationFrame(resetPageScroll)
    })

    return () => window.cancelAnimationFrame(firstFrame)
  }, [location.key, location.pathname, location.search])

  return null
}

function resetPageScroll() {
  window.scrollTo(0, 0)

  if (document.scrollingElement) {
    document.scrollingElement.scrollTop = 0
  }

  document.documentElement.scrollTop = 0
  document.body.scrollTop = 0
}
