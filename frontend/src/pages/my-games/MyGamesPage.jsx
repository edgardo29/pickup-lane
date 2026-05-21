import { AppPageHeader, AppPageShell, AppTabs } from '../../components/app/index.js'
import '../../styles/browse-games/BrowseGamesPage.css'
import '../../styles/my-games/MyGamesPage.css'
import HistoryGamesTab from './HistoryGamesTab.jsx'
import { MyGamesState } from './MyGamesState.jsx'
import UpcomingGamesTab from './UpcomingGamesTab.jsx'
import { myGamesTabs } from './myGamesData.js'
import { useMyGamesPageModel } from './useMyGamesPageModel.js'

function MyGamesPage() {
  const page = useMyGamesPageModel()

  return (
    <AppPageShell className="browse-page my-games-page">
      <AppPageHeader
        title="My Games"
        subtitle="Track the games you joined or hosted."
        tabs={
          <AppTabs
            ariaLabel="My games sections"
            items={myGamesTabs}
            onChange={page.setActiveTab}
            value={page.activeTab}
          />
        }
      />

      <section className="browse-panel my-games-panel" aria-label="My games">
        {page.status === 'loading' && <MyGamesState title="Loading your games" />}
        {page.status === 'error' && <MyGamesState title="Could not load games" message={page.error} />}
        {page.status === 'success' && page.activeItems.length === 0 && (
          <MyGamesState
            title={
              page.activeTab === 'history'
                ? 'No game history yet'
                : page.hasHiddenUpcomingItems
                  ? 'No games in this window'
                  : 'No upcoming games yet'
            }
            message={
              page.hasHiddenUpcomingItems
                ? 'You have games scheduled further out.'
                : 'Once you join or host a game, it will show up here.'
            }
          />
        )}

        {page.status === 'success' && (page.activeItems.length > 0 || page.hasMoreUpcomingItems) && (
          <div className="browse-results my-games-timeline">
            {page.activeTab === 'upcoming' ? (
              <UpcomingGamesTab
                groups={page.upcomingGroups}
                hasMoreItems={page.hasMoreUpcomingItems}
                imageUrlsByGameId={page.imageUrlsByGameId}
                participantCountsByGameId={page.participantCountsByGameId}
                onViewMore={page.showMoreUpcomingItems}
              />
            ) : (
              <HistoryGamesTab
                groups={page.historyGroups}
                imageUrlsByGameId={page.imageUrlsByGameId}
                participantCountsByGameId={page.participantCountsByGameId}
              />
            )}
          </div>
        )}
      </section>
    </AppPageShell>
  )
}

export default MyGamesPage
