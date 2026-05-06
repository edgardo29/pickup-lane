import { Link, NavLink } from 'react-router-dom'
import logo from '../assets/logo.png'

const navItems = [
  { label: 'Browse Games', to: '/games' },
  { label: 'My Games', to: '/my-games' },
  { label: 'Create Game', to: '/create-game' },
  { label: 'Inbox', to: '#inbox' },
  { label: 'Profile', to: '/profile' },
]

function BrowseAppNav() {
  return (
    <header className="browse-nav">
      <NavLink className="browse-nav__brand" to="/" aria-label="Pickup Lane home">
        <img src={logo} alt="" />
        <span>
          PICKUP <strong>LANE</strong>
        </span>
      </NavLink>

      <nav className="browse-nav__links" aria-label="Public navigation">
        {navItems.map((item) =>
          item.to.startsWith('#') ? (
            <a className="browse-nav__link" href={item.to} key={item.label}>
              {item.label}
            </a>
          ) : (
            <NavLink className="browse-nav__link" to={item.to} key={item.label}>
              {item.label}
            </NavLink>
          ),
        )}
      </nav>

      <div className="browse-nav__actions">
        <Link className="browse-nav__user" to="/profile" aria-label="Open profile">
          <span>AR</span>
          Alex Rivera
        </Link>
      </div>
    </header>
  )
}

export default BrowseAppNav
