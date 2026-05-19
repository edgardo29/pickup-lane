import AppNav from './AppNav.jsx'

function AppPageShell({ children, className = '', mainClassName = '', navProps = {} }) {
  return (
    <div className={`app-page ${className}`.trim()}>
      <AppNav {...navProps} />
      <main className={`app-page-shell ${mainClassName}`.trim()}>{children}</main>
    </div>
  )
}

export default AppPageShell
