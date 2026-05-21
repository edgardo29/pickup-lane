import BrowseAppNav from '../../components/BrowseAppNav.jsx'
import { ShieldCheckIcon } from '../../components/BrowseIcons.jsx'

export function DetailsScaffold({ state }) {
  return (
    <div className="details-page">
      <BrowseAppNav />
      <main className="details-shell">{state}</main>
    </div>
  )
}

export function DetailsState({ title, message }) {
  return (
    <div className="details-state">
      <h1>{title}</h1>
      {message && <p>{message}</p>}
    </div>
  )
}

export function StatusPill({ label }) {
  return (
    <div className="details-kicker">
      <ShieldCheckIcon />
      {label}
    </div>
  )
}
