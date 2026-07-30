import BrowseGameCard from './BrowseGameCard.jsx'
import { GameTimeIcon } from '../../components/GameFactIcons.jsx'
import { formatTimeGroupLabel } from './browseGameFormatters.js'

function BrowseTimeSection({ browseTimezone, group }) {
  const totalGames = group.totalGames ?? group.games.length
  const groupLabel = formatTimeGroupLabel(group.label)

  return (
    <section className="time-section">
      <div className="time-section__header">
        <h2 className="time-section__title">
          <span className="time-section__clock" aria-hidden="true">
            <GameTimeIcon />
          </span>
          <span className="time-section__label">{groupLabel}</span>
        </h2>
        <span className="time-section__rule" aria-hidden="true" />
        <span className="time-section__count">
          {totalGames} {totalGames === 1 ? 'game' : 'games'}
        </span>
      </div>

      <div className="time-section__grid">
        {group.games.map((game) => (
          <BrowseGameCard
            browseTimezone={browseTimezone}
            game={game}
            key={game.id}
          />
        ))}
      </div>
    </section>
  )
}

export default BrowseTimeSection
