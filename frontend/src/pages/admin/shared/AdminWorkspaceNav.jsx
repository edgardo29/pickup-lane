import { ShieldCheck } from 'lucide-react'
import { NavLink, useLocation } from 'react-router-dom'
import '../../../styles/admin/AdminWorkspace.css'
import { isAdminWorkspaceItemActive } from './adminWorkspaceData.js'

function AdminWorkspaceNav({ groups }) {
  const { pathname } = useLocation()

  return (
    <nav className="admin-workspace-nav" aria-label="Admin workspace navigation">
      <div className="admin-workspace-nav__identity">
        <ShieldCheck aria-hidden="true" />
        <div>
          <strong>Admin Tools</strong>
          <span>Operations</span>
        </div>
      </div>

      <div className="admin-workspace-nav__groups">
        {groups.map((group) => (
          <section
            className="admin-workspace-nav__group"
            aria-labelledby={`admin-nav-${group.id}`}
            key={group.id}
          >
            <h2 id={`admin-nav-${group.id}`}>
              <group.icon aria-hidden="true" />
              <span>{group.label}</span>
            </h2>
            <div className="admin-workspace-nav__items">
              {group.items.map((item) => (
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
                  <span>{item.label}</span>
                </NavLink>
              ))}
            </div>
          </section>
        ))}
      </div>
    </nav>
  )
}

export default AdminWorkspaceNav
