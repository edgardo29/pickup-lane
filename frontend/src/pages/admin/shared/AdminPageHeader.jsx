import '../../../styles/admin/AdminWorkspace.css'

function AdminPageHeader({
  actions,
  breadcrumbs = ['Admin'],
  description,
  icon: Icon,
  title,
}) {
  const sectionLabel = breadcrumbs.length > 2
    ? breadcrumbs[breadcrumbs.length - 2]
    : breadcrumbs.length === 2
      ? 'Overview'
      : ''

  return (
    <header className="admin-page-header">
      <div className="admin-page-header__copy">
        {sectionLabel && (
          <span className="admin-page-header__section">{sectionLabel}</span>
        )}

        <div className="admin-page-header__heading">
          {Icon && (
            <span className="admin-page-header__icon" aria-hidden="true">
              <Icon />
            </span>
          )}

          <div className="admin-page-header__text">
            <h1>{title}</h1>
            {description && (
              <p className="admin-page-header__description">{description}</p>
            )}
          </div>
        </div>
      </div>

      {actions && <div className="admin-page-header__actions">{actions}</div>}
    </header>
  )
}

export default AdminPageHeader
