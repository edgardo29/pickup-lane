import { AppPageHeader, AppPageShell, AppTabs } from '../../components/app/index.js'
import '../../styles/my-games/MyGamesPage.css'
import MyGameCard from './MyGameCard.jsx'
import MyGamesAgendaTab from './MyGamesAgendaTab.jsx'
import { MyGamesSkeleton } from './MyGamesSkeleton.jsx'
import { MyGamesState } from './MyGamesState.jsx'
import MyNeedASubCard from './MyNeedASubCard.jsx'
import { myGamesDomainTabs, myGamesViewTabs } from './myGamesData.js'
import { useMyGamesPageModel } from './useMyGamesPageModel.js'

function MyGamesPage() {
  const page = useMyGamesPageModel()
  const activeGroups = page.activeTab === 'upcoming'
    ? page.upcomingGroups
    : page.historyGroups
  const emptyCopy = getEmptyCopy(page.activeDomain, page.activeTab)
  const isNeedASubDomain = page.activeDomain === 'need-a-sub'
  const sectionTitle = getSectionTitle(page.activeTab)
  const timelineClassName = isNeedASubDomain
    ? 'my-games-timeline my-games-timeline--need-a-sub my-games-timeline--date-dividers'
    : 'my-games-timeline my-games-timeline--games my-games-timeline--date-dividers'

  return (
    <AppPageShell className="my-games-page">
      <AppPageHeader
        title="My Games"
        subtitle="Track your upcoming and recent activity."
        tabs={
          <AppTabs
            ariaLabel="My games domains"
            items={myGamesDomainTabs}
            onChange={page.setActiveDomain}
            value={page.activeDomain}
          />
        }
      />

      <section className="my-games-panel" aria-label={sectionTitle}>
        <div className="my-games-section-header">
          <h2>{sectionTitle}</h2>
          <AppTabs
            ariaLabel="My games views"
            items={myGamesViewTabs}
            onChange={page.setActiveTab}
            value={page.activeTab}
          />
        </div>

        {page.status === 'loading' && <MyGamesSkeleton />}
        {page.status === 'error' && (
          <MyGamesState
            actionLabel="Retry"
            message={page.error}
            onAction={page.retryActiveItems}
            title="Could not load My Games"
          />
        )}
        {page.status === 'success' && page.activeItems.length === 0 && (
          <MyGamesState
            title={emptyCopy.title}
            message={emptyCopy.message}
          />
        )}

        {page.status === 'success' && (page.activeItems.length > 0 || page.hasMoreItems) && (
          <div className={timelineClassName}>
            <MyGamesAgendaTab
              getItemKey={getAgendaItemKey}
              groups={activeGroups}
              hasMoreItems={page.hasMoreItems}
              isLoadingMore={page.isLoadingMore}
              itemLabel="game"
              loadMoreError={page.error}
              onLoadMore={page.loadMoreActiveItems}
              renderItem={(item) => (
                isNeedASubDomain ? (
                  <MyNeedASubCard item={item} />
                ) : (
                  <MyGameCard item={item} />
                )
              )}
              showGroupCounts
              variant={isNeedASubDomain ? 'need-a-sub' : 'games'}
            />
          </div>
        )}
      </section>
    </AppPageShell>
  )
}

function getSectionTitle(view) {
  return view === 'history'
    ? 'Game History'
    : 'Upcoming Games'
}

function getEmptyCopy(domain, view) {
  if (domain === 'need-a-sub') {
    return view === 'history'
      ? {
          title: 'No game history yet',
          message: 'Games you own or are confirmed for from the last 60 days will show up here.',
        }
      : {
          title: 'No upcoming games yet',
          message: 'Games you own or are confirmed for will show up here.',
        }
  }

  return view === 'history'
    ? {
        title: 'No game history yet',
        message: 'Hosted or confirmed games from the last 60 days will show up here.',
      }
    : {
        title: 'No upcoming games yet',
        message: 'Games you host or are confirmed for will show up here.',
      }
}

function getAgendaItemKey(item) {
  return item.game?.id || item.post?.id || item.participant_id || item.request_id
}

export default MyGamesPage
