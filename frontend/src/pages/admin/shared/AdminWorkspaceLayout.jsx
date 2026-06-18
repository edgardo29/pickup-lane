import AdminWorkspaceNav from './AdminWorkspaceNav.jsx'
import { getVisibleAdminWorkspaceNavItems } from './adminWorkspaceData.js'
import { useAdminAccess } from './useAdminAccess.js'

function AdminWorkspaceLayout({ children }) {
  const { adminAccess, isLoading } = useAdminAccess()
  const navItems = isLoading ? [] : getVisibleAdminWorkspaceNavItems(adminAccess)
  const layoutClassName = navItems.length
    ? 'admin-workspace-layout'
    : 'admin-workspace-layout admin-workspace-layout--single'

  return (
    <div className={layoutClassName}>
      {navItems.length > 0 && <AdminWorkspaceNav items={navItems} />}
      <div className="admin-workspace-content">
        {children}
      </div>
    </div>
  )
}

export default AdminWorkspaceLayout
