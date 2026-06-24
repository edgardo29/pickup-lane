import { Outlet } from 'react-router-dom'
import { AppPageShell } from '../../../components/app/index.js'
import '../../../styles/admin/AdminWorkspace.css'
import AdminWorkspaceNav from './AdminWorkspaceNav.jsx'
import { getVisibleAdminWorkspaceNavGroups } from './adminWorkspaceData.js'
import { useAdminAccess } from './useAdminAccess.js'

function AdminWorkspaceShell() {
  const { adminAccess } = useAdminAccess()
  const navGroups = getVisibleAdminWorkspaceNavGroups(adminAccess)

  return (
    <AppPageShell className="admin-page" mainClassName="admin-shell">
      <div className="admin-workspace-layout">
        <AdminWorkspaceNav groups={navGroups} />
        <Outlet />
      </div>
    </AppPageShell>
  )
}

export default AdminWorkspaceShell
