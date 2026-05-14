import { useLayoutEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import BrandMark from '../../components/BrandMark.jsx'
import { ArrowLeftIcon } from '../../components/AuthIcons.jsx'
import '../../styles/auth/AuthShared.css'
import '../../styles/auth/AuthShell.css'

export function AuthShell({
  backDisabled = false,
  backLabel = 'Home',
  backTo = '/',
  children,
  onBack,
  showBack = true,
  variant = 'default',
}) {
  const location = useLocation()

  useLayoutEffect(() => {
    resetAuthScroll()

    const frame = window.requestAnimationFrame(() => {
      resetAuthScroll()
    })
    const delayedReset = window.setTimeout(resetAuthScroll, 80)

    return () => {
      window.cancelAnimationFrame(frame)
      window.clearTimeout(delayedReset)
    }
  }, [location.key, location.pathname, location.search])

  function handleAuthNavigation(event) {
    const link = event.target.closest?.('a[href]')

    if (!link || link.target || link.hasAttribute('download')) {
      return
    }

    const nextUrl = new URL(link.href)

    if (nextUrl.origin === window.location.origin) {
      resetAuthScroll()
    }
  }

  return (
    <main className={`auth-page auth-page--${variant}`} onClickCapture={handleAuthNavigation}>
      {showBack && (
        onBack ? (
          <button
            aria-label={backLabel}
            className="auth-back-control"
            disabled={backDisabled}
            onClick={onBack}
            type="button"
          >
            <span className="auth-back-control__icon">
              <ArrowLeftIcon />
            </span>
          </button>
        ) : (
          <Link className="auth-back-control" to={backTo} aria-label={backLabel}>
            <span className="auth-back-control__icon">
              <ArrowLeftIcon />
            </span>
          </Link>
        )
      )}

      <div className="auth-frame">
        <Link className="auth-frame__brand" to="/" aria-label="Pickup Lane home">
          <BrandMark compact />
        </Link>

        {children}
      </div>
    </main>
  )
}

function resetAuthScroll() {
  window.scrollTo(0, 0)

  if (document.scrollingElement) {
    document.scrollingElement.scrollTop = 0
  }

  document.documentElement.scrollTop = 0
  document.body.scrollTop = 0
}
