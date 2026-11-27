import { AppPageHeader, AppPageShell, AppTabs } from '../../components/app/index.js'
import '../../styles/inbox/InboxPage.css'
import InboxSection from './InboxSection.jsx'
import { InboxState } from './InboxState.jsx'
import NotificationModal from './NotificationModal.jsx'
import { GAME_ACTIVITY_TAB, inboxTabs } from './inboxData.js'
import { useInboxPageModel } from './useInboxPageModel.js'

function InboxPage() {
  const page = useInboxPageModel()
  const tabItems = inboxTabs.map((tab) => {
    const section = page.inboxSections.find((item) => item.key === tab.key)
    const count = section?.count ?? 0
    const countMeaning = tab.key === GAME_ACTIVITY_TAB ? 'unread' : 'new'

    return {
      key: tab.key,
      label: (
        <span className="inbox-tab-label">
          {tab.label}
          <span className="inbox-tab-label__count" aria-hidden="true">{count}</span>
          <span className="inbox-tab-label__spoken">{`, ${count} ${countMeaning}`}</span>
        </span>
      ),
    }
  })

  return (
    <AppPageShell className="inbox-page" mainClassName="inbox-shell">
      <AppPageHeader
        title="Inbox"
        subtitle="Review notifications and game activity."
        tabs={
          <AppTabs
            ariaLabel="Inbox filters"
            items={tabItems}
            onChange={page.setActiveFilter}
            value={page.activeFilter}
          />
        }
      />

      {page.status === 'loading' && <InboxState title="Loading inbox" />}
      {page.status === 'error' && <InboxState title="Could not load inbox" message={page.error} />}

      {page.status === 'success' && (
        <div className="inbox-tab-panel">
          {page.filteredSections.map((section) => (
            <InboxSection
              emptyMessage={section.emptyMessage}
              emptyTitle={section.emptyTitle}
              items={section.items}
              key={section.key}
              onLoadMore={page.handleLoadMore}
              onOpenNotification={page.handleOpenNotification}
              onSourceFilterChange={page.handleSourceFilterChange}
              section={section}
            />
          ))}
        </div>
      )}

      {page.activeNotification && (
        <NotificationModal
          notification={page.activeNotification}
          onClose={() => page.setActiveNotification(null)}
          onNotificationAction={page.handleNotificationAction}
        />
      )}
    </AppPageShell>
  )
}

export default InboxPage
