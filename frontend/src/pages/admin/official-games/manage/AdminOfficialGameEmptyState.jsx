function AdminOfficialGameEmptyState({ children, icon: Icon, title }) {
  return (
    <div className="admin-manage-empty-state">
      {Icon && (
        <span className="admin-manage-empty-state__icon">
          <Icon />
        </span>
      )}
      <div>
        <strong>{title}</strong>
        {children && <p>{children}</p>}
      </div>
    </div>
  )
}

export default AdminOfficialGameEmptyState
