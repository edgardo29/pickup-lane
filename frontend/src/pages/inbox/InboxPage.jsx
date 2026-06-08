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
    <AppPageShell className="inbox-page" mainClassName="inbox-shell">
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

      {page.status === 'success' && (
        <>
          <div className="inbox-desktop-grid">
            {page.inboxSections.map((section) => (
              <InboxSection
                emptyMessage={section.emptyMessage}
                emptyTitle={section.emptyTitle}
                items={section.items}
                key={section.key}
                onOpenNotification={page.handleOpenNotification}
                onSourceFilterChange={page.handleSourceFilterChange}
                section={section}
              />
            ))}
          </div>

          <div className="inbox-mobile-stack">
            {page.filteredSections.map((section) => (
              <InboxSection
                emptyMessage={section.emptyMessage}
                emptyTitle={section.emptyTitle}
                items={section.items}
                key={section.key}
                onOpenNotification={page.handleOpenNotification}
                onSourceFilterChange={page.handleSourceFilterChange}
                section={section}
                showHeader={false}
              />
            ))}
          </div>
        </>
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
