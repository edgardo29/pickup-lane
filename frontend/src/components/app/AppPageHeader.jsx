function AppPageHeader({ actions, eyebrow, subtitle, tabs, title }) {
  const supportingText = subtitle || eyebrow

  return (
    <header className={tabs ? 'app-page-header app-page-header--with-tabs' : 'app-page-header'}>
      <div className="app-page-header__top">
        <div className="app-page-header__copy">
          <h1>{title}</h1>
          {supportingText && <p className="app-page-header__subtitle">{supportingText}</p>}
        </div>
        {actions && <div className="app-page-header__actions">{actions}</div>}
      </div>

      {tabs && (
        <div className="app-page-header__tabs">
          {tabs}
        </div>
      )}
    </header>
  )
}

export default AppPageHeader
