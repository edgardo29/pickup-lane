import { AppCardGrid } from '../../components/app/index.js'
import { CalendarIcon } from '../../components/BrowseIcons.jsx'

function MyGamesAgendaTab({
  getItemKey,
  groups,
  hasMoreItems,
  itemLabel = 'game',
  isLoadingMore,
  loadMoreError = '',
  onLoadMore,
  renderItem,
  showGroupCounts = false,
  variant = 'games',
}) {
  return (
    <>
      {groups.map((dateGroup) => (
        <section className={`my-games-agenda-day my-games-agenda-day--${variant}`} key={dateGroup.key}>
          <div className="my-games-agenda-day__header">
            <h2>
              <CalendarIcon />
              <span className="my-games-agenda-day__label">{dateGroup.label}</span>
            </h2>
            {showGroupCounts && (
              <>
                <span className="my-games-agenda-day__rule" aria-hidden="true" />
                <span className="my-games-agenda-day__count">
                  {dateGroup.items.length} {dateGroup.items.length === 1 ? itemLabel : `${itemLabel}s`}
                </span>
              </>
            )}
          </div>

          <AppCardGrid className="my-games-agenda-grid">
            {dateGroup.items.map((item) => (
              <div className="my-games-agenda-grid__item" key={getItemKey(item)}>
                {renderItem(item)}
              </div>
            ))}
          </AppCardGrid>
        </section>
      ))}

      {loadMoreError && (
        <div className="my-games-load-more-error" role="alert">
          <span>{loadMoreError}</span>
          <button type="button" onClick={onLoadMore} disabled={isLoadingMore}>
            {isLoadingMore ? 'Retrying...' : 'Retry'}
          </button>
        </div>
      )}

      {hasMoreItems && !loadMoreError && (
        <button
          className="my-games-view-more"
          type="button"
          onClick={onLoadMore}
          disabled={isLoadingMore}
        >
          {isLoadingMore ? 'Loading...' : 'Load More'}
        </button>
      )}
    </>
  )
}

export default MyGamesAgendaTab
