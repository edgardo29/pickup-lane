import { SoccerBallIcon } from '../../components/BrowseIcons.jsx'

export function MyGamesState({ actionLabel = '', message, onAction, title }) {
  return (
    <div className="my-games-state">
      <SoccerBallIcon />
      <h2>{title}</h2>
      {message && <p>{message}</p>}
      {actionLabel && onAction && (
        <button className="my-games-state__action" type="button" onClick={onAction}>
          {actionLabel}
        </button>
      )}
    </div>
  )
}
