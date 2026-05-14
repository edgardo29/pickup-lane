import BrowseGameCard from './BrowseGameCard.jsx'
import { ClockIcon } from '../../components/BrowseIcons.jsx'

function BrowseTimeSection({ group, imageUrlsByGameId, participantCountsByGameId }) {
  return (
    <section className="time-section">
      <div className="time-section__header">
        <h2>
          <ClockIcon />
          {group.label}
        </h2>
        <span className="time-section__count">
          {group.games.length} {group.games.length === 1 ? 'game' : 'games'}
        </span>
      </div>

      <div className="time-section__grid">
        {group.games.map((game) => (
          <BrowseGameCard
            game={game}
            imageUrl={imageUrlsByGameId.get(game.id)}
            signedUpCount={participantCountsByGameId.get(game.id) || 0}
            key={game.id}
          />
        ))}
      </div>
    </section>
  )
}

export default BrowseTimeSection
