import { SoccerBallIcon } from '../../components/BrowseIcons.jsx'

export function BrowseState({ action, message, title }) {
  return (
    <div className="browse-state">
      <SoccerBallIcon />
      <h2>{title}</h2>
      {message && <p>{message}</p>}
      {action && <div className="browse-state__action">{action}</div>}
    </div>
  )
}
