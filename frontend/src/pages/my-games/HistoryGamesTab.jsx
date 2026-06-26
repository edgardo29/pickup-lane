import { AppCardGrid } from '../../components/app/index.js'
import { CalendarIcon } from '../../components/BrowseIcons.jsx'
import MyGameCard from './MyGameCard.jsx'

function HistoryGamesTab({ groups, hasMoreItems, isLoadingMore, onLoadMore }) {
  return (
    <>
      {groups.map((dateGroup) => (
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
                item={item}
                key={item.participant_id || item.game.id}
              />
            ))}
          </AppCardGrid>
        </section>
      ))}

      {hasMoreItems && (
        <button
          className="my-games-view-more"
          type="button"
          onClick={onLoadMore}
          disabled={isLoadingMore}
        >
          {isLoadingMore ? 'Loading…' : 'Load More'}
        </button>
      )}
    </>
  )
}

export default HistoryGamesTab
