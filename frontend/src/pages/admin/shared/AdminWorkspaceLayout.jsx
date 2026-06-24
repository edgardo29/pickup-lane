import AdminWorkspaceNav from './AdminWorkspaceNav.jsx'
import AdminPageHeader from './AdminPageHeader.jsx'
import { getVisibleAdminWorkspaceNavGroups } from './adminWorkspaceData.js'
import { useAdminAccess } from './useAdminAccess.js'

function AdminWorkspaceLayout({
  actions,
  breadcrumbs,
  children,
  description,
  icon,
  title,
}) {
  const { adminAccess, isLoading } = useAdminAccess()
  const navGroups = isLoading ? [] : getVisibleAdminWorkspaceNavGroups(adminAccess)
  const layoutClassName = navGroups.length
    ? 'admin-workspace-layout'
    : 'admin-workspace-layout admin-workspace-layout--single'

  return (
    <div className={layoutClassName}>
      {navGroups.length > 0 && <AdminWorkspaceNav groups={navGroups} />}
      <div className="admin-workspace-content">
        <AdminPageHeader
          actions={actions}
          breadcrumbs={breadcrumbs}
          description={description}
          icon={icon}
          title={title}
        />
        <div className="admin-workspace-body">
          {children}
        </div>
      </div>
    </div>
  )
}

export default AdminWorkspaceLayout
