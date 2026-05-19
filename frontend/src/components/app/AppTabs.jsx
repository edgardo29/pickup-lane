function AppTabs({ ariaLabel, items, onChange, value }) {
  return (
    <div className="app-tabs" role="tablist" aria-label={ariaLabel}>
      {items.map((item) => (
        <button
          className={value === item.key ? 'active' : ''}
          type="button"
          role="tab"
          aria-selected={value === item.key}
          key={item.key}
          onClick={() => onChange(item.key)}
        >
          {item.label}
        </button>
      ))}
    </div>
  )
}

export default AppTabs
