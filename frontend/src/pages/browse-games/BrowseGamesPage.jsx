import BrowseAppNav from '../../components/BrowseAppNav.jsx'
import '../../styles/browse-games/BrowseGamesPage.css'
import BrowseDateStrip from './BrowseDateStrip.jsx'
import { BrowseState } from './BrowseState.jsx'
import BrowseTimeSection from './BrowseTimeSection.jsx'
import { useBrowseGamesPageModel } from './useBrowseGamesPageModel.js'

function BrowseGamesPage() {
  const page = useBrowseGamesPageModel()

  return (
    <div className="browse-page">
      <BrowseAppNav />

      <main className="browse-shell">
        <section className="browse-hero" aria-labelledby="browse-title">
          <div className="browse-hero__copy">
            <h1 id="browse-title">
              <span>Browse</span>
              <span>Games</span>
            </h1>
            <p>Find open pickup games near you.</p>
          </div>
        </section>

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

          {page.status === 'loading' && <BrowseState title="Loading games" />}
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
      </main>
    </div>
  )
}

export default BrowseGamesPage
