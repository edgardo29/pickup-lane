import { NavLink, useLocation } from 'react-router-dom'
import '../../../styles/admin/AdminWorkspace.css'
import { isAdminWorkspaceItemActive } from './adminWorkspaceData.js'

function AdminWorkspaceNav({ items }) {
  const { pathname } = useLocation()

  return (
    <nav className="admin-workspace-nav" aria-label="Admin workspace navigation">
      {items.map((item) => (
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
