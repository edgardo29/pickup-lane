import { AppPageHeader, AppPageShell } from '../../components/app/index.js'
import '../../styles/browse-games/BrowseGamesPage.css'
import BrowseDateStrip from './BrowseDateStrip.jsx'
import { BrowseGamesSkeleton } from './BrowseGamesSkeleton.jsx'
import { BrowseState } from './BrowseState.jsx'
import BrowseTimeSection from './BrowseTimeSection.jsx'
import { useBrowseGamesPageModel } from './useBrowseGamesPageModel.js'

function BrowseGamesPage() {
  const page = useBrowseGamesPageModel()

  return (
    <AppPageShell className="browse-page" mainClassName="browse-shell">
      {page.status === 'loading' ? (
        <BrowseGamesSkeleton />
      ) : (
        <div className="browse-content pl-motion-enter pl-motion-enter--fade">
          <AppPageHeader title="Browse Games" subtitle="Find open pickup games near you." />

          <section className="browse-panel" aria-label="Available games">
            <BrowseDateStrip
              canGoNext={page.canGoNextDates}
              canGoPrevious={page.canGoPreviousDates}
              dates={page.visibleDateOptions}
              onNext={() => page.selectDatePage(page.datePageIndex + 1)}
              onPrevious={() => page.selectDatePage(page.datePageIndex - 1)}
              selectedDateKey={page.activeDateKey}
              onSelectDate={page.setSelectedDateKey}
            />

            {page.status === 'error' && (
              <BrowseState
                title="Could not load games"
                message={page.error}
                action={(
                  <button type="button" onClick={page.retryFirstPage}>
                    Retry
                  </button>
                )}
              />
            )}
            {page.status === 'success' && page.timeGroups.length === 0 && (
              <BrowseState title="No games found" message="Try another date or check back soon." />
            )}

            {page.status === 'success' && page.timeGroups.length > 0 && (
              <>
                <div className="browse-results">
                  {page.timeGroups.map((group) => (
                    <BrowseTimeSection
                      browseTimezone={page.browseTimezone}
                      group={group}
                      key={group.key}
                    />
                  ))}
                </div>

                {page.hasMoreGames && (
                  <div className="browse-load-more">
                    {page.loadMoreError && (
                      <p className="browse-load-more__error">{page.loadMoreError}</p>
                    )}
                    <button
                      type="button"
                      onClick={page.loadMoreError ? page.retryLoadMore : page.loadMoreGames}
                      disabled={page.isLoadingMore}
                    >
                      {page.isLoadingMore ? 'Loading...' : page.loadMoreError ? 'Retry' : 'Load More'}
                    </button>
                  </div>
                )}
              </>
            )}
          </section>
        </div>
      )}
    </AppPageShell>
  )
}

export default BrowseGamesPage
