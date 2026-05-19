function AppPageHeader({ actions, eyebrow, tabs, title }) {
  return (
    <header className="app-page-header">
      <div className="app-page-header__copy">
        {eyebrow && <p>{eyebrow}</p>}
        <h1>{title}</h1>
        {tabs && <div className="app-page-header__tabs">{tabs}</div>}
      </div>
      {actions && <div className="app-page-header__actions">{actions}</div>}
    </header>
  )
}

export default AppPageHeader
