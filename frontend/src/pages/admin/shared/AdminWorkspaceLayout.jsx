import AdminPageHeader from './AdminPageHeader.jsx'

function AdminWorkspaceLayout({
  actions,
  breadcrumbs,
  children,
  description,
  icon,
  title,
}) {
  return (
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
  )
}

export default AdminWorkspaceLayout
