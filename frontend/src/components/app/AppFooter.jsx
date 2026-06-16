import { Link } from 'react-router-dom'
import logoNav from '../../assets/logo-nav.png'

const footerGroups = [
  {
    title: 'Play',
    links: [
      { label: 'Browse Games', to: '/games' },
      { label: 'Need a Sub', to: '/need-a-sub' },
      { label: 'Create Game', to: '/create-game' },
    ],
  },
  {
    title: 'Account',
    links: [
      { label: 'Sign In', to: '/sign-in' },
      { label: 'Create Account', to: '/create-account' },
      { label: 'My Games', to: '/my-games' },
    ],
  },
  {
    title: 'Policies',
    links: [
      { label: 'Terms of Service', to: '/terms' },
      { label: 'Privacy Policy', to: '/privacy' },
      { label: 'Cancellation & Refunds', to: '/policies/cancellation-refunds' },
    ],
  },
]

function AppFooter() {
  const year = new Date().getFullYear()

  return (
    <footer className="app-footer" aria-label="Footer">
      <div className="app-footer__inner">
        <section className="app-footer__brand" aria-label="Pickup Lane">
          <Link className="app-footer__brand-link" to="/" aria-label="Pickup Lane home">
            <span className="app-footer__brand-logo" aria-hidden="true">
              <img
                src={logoNav}
                alt=""
                width="614"
                height="538"
                loading="lazy"
                decoding="async"
              />
            </span>
            <span className="app-footer__brand-wordmark">
              PICKUP <strong>LANE</strong>
            </span>
          </Link>

          <p>Find real pickup soccer games, join approved venues, and keep your next run organized.</p>
        </section>

        <nav className="app-footer__nav" aria-label="Footer navigation">
          {footerGroups.map((group) => (
            <section className="app-footer__group" key={group.title}>
              <h2>{group.title}</h2>
              <ul>
                {group.links.map((link) => (
                  <li key={link.to}>
                    <Link to={link.to}>{link.label}</Link>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </nav>

        <div className="app-footer__bottom">
          <p>&copy; {year} Pickup Lane. All rights reserved.</p>
          <p>Built for players who just want the game to happen.</p>
        </div>
      </div>
    </footer>
  )
}

export default AppFooter
