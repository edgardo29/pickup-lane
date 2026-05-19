import { AppCardGrid } from '../../components/app/index.js'
import { CalendarIcon } from '../../components/BrowseIcons.jsx'
import MyGameCard from './MyGameCard.jsx'

function HistoryGamesTab({ groups, imageUrlsByGameId, participantCountsByGameId }) {
  return groups.map((dateGroup) => (
    <section className="my-games-agenda-day" key={dateGroup.key}>
      <div className="time-section__header my-games-agenda-day__header">
        <h2>
          <CalendarIcon />
          {dateGroup.label}
        </h2>
      </div>

      <AppCardGrid className="my-games-agenda-grid">
        {dateGroup.items.map((item) => (
          <MyGameCard
            imageUrl={imageUrlsByGameId.get(item.game.id)}
            item={item}
            participantCount={participantCountsByGameId.get(item.game.id) || 0}
            key={item.participant.id}
          />
        ))}
      </AppCardGrid>
    </section>
  ))
}

export default HistoryGamesTab
