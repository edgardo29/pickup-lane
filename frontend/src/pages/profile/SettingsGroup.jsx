import { Link } from 'react-router-dom'
import { ChevronRightIcon } from './ProfileIcons.jsx'

export function SettingsGroup({ title, rows = [] }) {
  return (
    <section className="settings-group">
      <h2>{title}</h2>
      <div className="settings-group__rows">
        {rows.map((row) => (
          <SettingsRow key={row.title} row={row} />
        ))}
      </div>
    </section>
  )
}

export function SettingsRow({ row }) {
  const rowClassName = `settings-row ${row.tone === 'danger' ? 'settings-row--danger' : ''}`
  const content = (
    <>
      <span className="settings-row__icon">{row.icon}</span>
      <span>
        <strong>{row.title}</strong>
        <small>{row.text}</small>
      </span>
      <ChevronRightIcon />
    </>
  )

  if (row.to) {
    return (
      <Link className={rowClassName} state={row.state} to={row.to}>
        {content}
      </Link>
    )
  }

  return (
    <button
      className={rowClassName}
      onClick={row.onClick}
      type="button"
    >
      {content}
    </button>
  )
}
