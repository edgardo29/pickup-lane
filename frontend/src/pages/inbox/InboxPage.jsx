import { AppPageHeader, AppPageShell, AppTabs } from '../../components/app/index.js'
import '../../styles/inbox/InboxPage.css'
import InboxSection from './InboxSection.jsx'
import { InboxState } from './InboxState.jsx'
import NotificationModal from './NotificationModal.jsx'
import { inboxTabs } from './inboxData.js'
import { useInboxPageModel } from './useInboxPageModel.js'

function InboxPage() {
  const page = useInboxPageModel()

  return (
    <AppPageShell className="inbox-page" mainClassName="app-page-shell--narrow inbox-shell">
      <AppPageHeader
        title="Inbox"
        subtitle="Review notifications and game activity."
        tabs={
          <AppTabs
            ariaLabel="Inbox filters"
            items={inboxTabs}
            onChange={page.setActiveFilter}
            value={page.activeFilter}
          />
        }
      />

      {page.status === 'loading' && <InboxState title="Loading inbox" />}
      {page.status === 'error' && <InboxState title="Could not load inbox" message={page.error} />}

      {page.status === 'success' && page.notifications.length === 0 && (
        <InboxState title="Nothing here yet" message="Your updates will show up here." />
      )}

      {page.status === 'success' && page.notifications.length > 0 && (
        <div className="inbox-section-stack">
          {page.filteredSections.map((section) => (
            <InboxSection
              gamesById={page.gamesById}
              items={section.items}
              key={section.title}
              onOpenNotification={page.handleOpenNotification}
              section={section}
            />
          ))}
        </div>
      )}

      {page.hasNoMatchingUpdates && (
        <InboxState title="No matching updates" message="Try another inbox filter." />
      )}

      {page.activeNotification && (
        <NotificationModal
          game={page.gamesById.get(page.activeNotification.related_game_id)}
          notification={page.activeNotification}
          onClose={() => page.setActiveNotification(null)}
          onViewGame={page.handleViewGame}
        />
      )}
    </AppPageShell>
  )
}

export default InboxPage
