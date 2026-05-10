import { Link } from 'react-router-dom'
import BrandMark from './BrandMark.jsx'
import { useAuth } from '../hooks/useAuth.js'

const guestNavLinks = [
  { label: 'How it Works', href: '#how-it-works' },
  { label: 'Browse Games', to: '/games' },
  { label: 'Need a Sub', to: '/need-a-sub' },
]

const signedInNavLinks = [
  { label: 'Browse Games', to: '/games' },
  { label: 'My Games', to: '/my-games' },
  { label: 'Create Game', to: '/create-game' },
  { label: 'Need a Sub', to: '/need-a-sub' },
  { label: 'Inbox', to: '/inbox' },
  { label: 'Profile', to: '/profile' },
]

function SiteNav() {
  const { appUser, currentUser, isLoading } = useAuth()
  const navLinks = isLoading ? [] : appUser ? signedInNavLinks : guestNavLinks
  const displayName = appUser ? getDisplayName(appUser, currentUser) : 'Sign In'
  const initials = getInitials(appUser, currentUser)

  return (
    <header className="site-nav">
      <Link className="site-nav__brand" to="/" aria-label="Pickup Lane home">
        <BrandMark compact />
      </Link>

      <nav className="site-nav__links" aria-label="Main navigation">
        {navLinks.map((link) =>
          link.to ? (
            <Link key={link.to} to={link.to}>
              {link.label}
            </Link>
          ) : (
            <a key={link.href} href={link.href}>
              {link.label}
            </a>
          ),
        )}
      </nav>

      {isLoading ? (
        <span className="site-nav__placeholder" aria-hidden="true" />
      ) : (
        <Link
          className={`site-nav__signin ${appUser ? 'site-nav__signin--user' : ''}`}
          to={appUser ? '/profile' : '/sign-in'}
        >
          {appUser && <span>{initials}</span>}
          {displayName}
        </Link>
      )}
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

export default SiteNav
