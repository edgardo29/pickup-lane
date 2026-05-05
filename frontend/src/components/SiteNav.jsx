import { Link } from 'react-router-dom'
import BrandMark from './BrandMark.jsx'

const navLinks = [
  { label: 'How it Works', href: '#how-it-works' },
  { label: 'Browse Games', to: '/games' },
  { label: 'Player Hub', href: '#player-hub' },
  { label: 'Host a Game', href: '#host' },
]

function SiteNav() {
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

      <Link className="site-nav__signin" to="/sign-in">
        Sign In
      </Link>
    </header>
  )
}

export default SiteNav
