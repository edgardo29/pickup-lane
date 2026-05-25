import { NavLink, useLocation } from 'react-router-dom'
import '../../../styles/admin/AdminWorkspace.css'
import { adminWorkspaceNavItems } from './adminWorkspaceData.js'

function isAdminWorkspaceItemActive(item, pathname) {
  if (item.to === '/admin/official-games') {
    return (
      pathname === item.to
      || (pathname.startsWith('/admin/official-games/') && pathname !== '/admin/official-games/new')
    )
  }

  return pathname === item.to
}

function AdminWorkspaceNav() {
  const { pathname } = useLocation()

  return (
    <nav className="admin-workspace-nav" aria-label="Admin workspace navigation">
      {adminWorkspaceNavItems.map((item) => (
        <NavLink
          className={() => {
            const classNames = ['admin-workspace-nav__link']
            if (isAdminWorkspaceItemActive(item, pathname)) {
              classNames.push('active')
            }
            return classNames.join(' ')
          }}
          end={item.end}
          key={item.to}
          to={item.to}
        >
          {item.label}
        </NavLink>
      ))}
    </nav>
  )
}

export default AdminWorkspaceNav
