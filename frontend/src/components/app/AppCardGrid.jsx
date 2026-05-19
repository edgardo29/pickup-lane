function AppCardGrid({ children, className = '' }) {
  return <div className={`app-card-grid ${className}`.trim()}>{children}</div>
}

export default AppCardGrid
