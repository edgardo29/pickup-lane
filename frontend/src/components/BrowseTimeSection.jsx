import BrowseGameCard from './BrowseGameCard.jsx'

function BrowseTimeSection({ group, imageUrlsByGameId, participantCountsByGameId }) {
  return (
    <section className="time-section">
      <div className="time-section__header">
        <h2>{group.label}</h2>
        <span>
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
