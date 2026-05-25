import AdminWorkspaceNav from './AdminWorkspaceNav.jsx'

function AdminWorkspaceLayout({ children }) {
  return (
    <div className="admin-workspace-layout">
      <AdminWorkspaceNav />
      <div className="admin-workspace-content">
        {children}
      </div>
    </div>
  )
}

export default AdminWorkspaceLayout
