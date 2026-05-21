import { SoccerBallIcon } from '../../components/BrowseIcons.jsx'

export function MyGamesState({ title, message }) {
  return (
    <div className="my-games-state">
      <SoccerBallIcon />
      <h2>{title}</h2>
      {message && <p>{message}</p>}
    </div>
  )
}
