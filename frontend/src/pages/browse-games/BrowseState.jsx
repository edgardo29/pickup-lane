import { SoccerBallIcon } from '../../components/BrowseIcons.jsx'

export function BrowseState({ title, message }) {
  return (
    <div className="browse-state">
      <SoccerBallIcon />
      <h2>{title}</h2>
      {message && <p>{message}</p>}
    </div>
  )
}
