import { Link, NavLink } from 'react-router-dom'
import { useEffect, useState } from 'react'
import logo from '../assets/logo.png'
import { apiRequest } from '../lib/apiClient.js'

const DEMO_CURRENT_USER_AUTH_ID = 'demo-current-user'

const navItems = [
  { label: 'Browse Games', to: '/games' },
  { label: 'My Games', to: '/my-games' },
  { label: 'Create Game', to: '/create-game' },
  { label: 'Inbox', to: '/inbox' },
  { label: 'Profile', to: '/profile' },
]

function BrowseAppNav() {
  const [unreadCount, setUnreadCount] = useState(0)

  useEffect(() => {
    let ignore = false

    async function loadUnreadCount() {
      try {
        const usersResponse = await apiRequest('/users')
        const demoUser = usersResponse.find((user) => user.auth_user_id === DEMO_CURRENT_USER_AUTH_ID)

        if (!demoUser) {
          return
        }

        const unreadNotifications = await apiRequest(
          `/notifications?user_id=${demoUser.id}&is_read=false`,
        )

        if (!ignore) {
          setUnreadCount(unreadNotifications.length)
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
  }, [])

  return (
    <header className="browse-nav">
      <NavLink className="browse-nav__brand" to="/" aria-label="Pickup Lane home">
        <img src={logo} alt="" />
        <span>
          PICKUP <strong>LANE</strong>
        </span>
      </NavLink>

      <nav className="browse-nav__links" aria-label="Public navigation">
        {navItems.map((item) => (
          <NavLink className="browse-nav__link" to={item.to} key={item.label}>
            {item.label}
            {item.label === 'Inbox' && unreadCount > 0 && (
              <span className="browse-nav__badge">{unreadCount}</span>
            )}
          </NavLink>
        ))}
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
