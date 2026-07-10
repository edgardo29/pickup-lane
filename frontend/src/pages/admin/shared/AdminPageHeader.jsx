import '../../../styles/admin/AdminWorkspace.css'

function AdminPageHeader({
  actions,
  breadcrumbs = ['Admin'],
  className = '',
  description,
  icon: Icon,
  title,
}) {
  const headerClassName = [
    'admin-page-header',
    className,
  ].filter(Boolean).join(' ')
  const sectionLabel = breadcrumbs.length > 2
    ? breadcrumbs[breadcrumbs.length - 2]
    : breadcrumbs.length === 2
      ? 'Overview'
      : ''

  return (
    <header className={headerClassName}>
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
