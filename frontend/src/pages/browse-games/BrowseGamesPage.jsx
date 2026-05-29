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
        <>
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

            {page.status === 'error' && <BrowseState title="Could not load games" message={page.error} />}
            {page.status === 'success' && page.timeGroups.length === 0 && (
              <BrowseState title="No games found" message="Try another date or check back soon." />
            )}

            {page.status === 'success' && page.timeGroups.length > 0 && (
              <div className="browse-results">
                {page.timeGroups.map((group) => (
                  <BrowseTimeSection
                    group={group}
                    imageUrlsByGameId={page.imageUrlsByGameId}
                    participantCountsByGameId={page.participantCountsByGameId}
                    key={group.label}
                  />
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </AppPageShell>
  )
}

export default BrowseGamesPage
