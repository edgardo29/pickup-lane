import BrandMark from './BrandMark.jsx'

const navLinks = [
  { label: 'How it Works', href: '#how-it-works' },
  { label: 'Browse Games', href: '#browse' },
  { label: 'Host a Game', href: '#host' },
]

function SiteNav() {
  return (
    <header className="site-nav">
      <a className="site-nav__brand" href="/" aria-label="Pickup Lane home">
        <BrandMark compact />
      </a>

      <nav className="site-nav__links" aria-label="Main navigation">
        {navLinks.map((link) => (
          <a key={link.href} href={link.href}>
            {link.label}
          </a>
        ))}
      </nav>

      <a className="site-nav__signin" href="#signin">
        Sign In
      </a>
    </header>
  )
}

export default SiteNav
