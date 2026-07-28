import { ChatIcon } from '../../components/BrowseIcons.jsx'
import { InboxState } from './InboxState.jsx'
import InboxRow from './InboxRow.jsx'
import { getInboxItemKey } from './inboxData.js'

function InboxSection({
  emptyMessage = 'Your updates will show up here.',
  emptyTitle = 'Nothing here yet',
  items,
  onLoadMore,
  onOpenNotification,
  onSourceFilterChange,
  section,
  showHeader = true,
}) {
  const isFilteredEmpty = section.totalItems > 0 && items.length === 0
  const countLabel = String(section.count ?? 0)

  return (
    <section className="inbox-section">
      {showHeader && (
        <div className="inbox-section__heading">
          {section.key === 'game' ? <ChatIcon /> : <MegaphoneIcon />}
          <div>
            <h2>{section.title}</h2>
          </div>
          <span>{countLabel}</span>
        </div>
      )}

      {section.statusFilterOptions?.length > 0 && (
        <div className="inbox-section__filter">
          <span className="inbox-section__select-control">
            <select
              aria-label={`Filter ${section.title}`}
              value={section.statusFilterValue}
              onChange={(event) => onSourceFilterChange(section.key, event.target.value)}
            >
              {section.statusFilterOptions.map((option) => (
                <option key={option.key} value={option.key}>
                  {option.label}
                </option>
              ))}
            </select>
            <span className="inbox-section__select-chevron" aria-hidden="true" />
          </span>
        </div>
      )}

      {items.length === 0 ? (
        <InboxState
          compact
          title={isFilteredEmpty ? 'No matching notifications' : emptyTitle}
          message={isFilteredEmpty ? 'Try another source filter.' : emptyMessage}
        />
      ) : (
        <>
          <div className="inbox-list">
            {items.map((notification) => (
              <InboxRow
                key={getInboxItemKey(notification)}
                notification={notification}
                onOpenNotification={onOpenNotification}
              />
            ))}
          </div>
          {(section.hasMore || section.loadMoreError) && (
            <div className="inbox-section__pagination">
              {section.loadMoreError && (
                <p className="inbox-section__pagination-error">
                  {section.loadMoreError}
                </p>
              )}
              {section.hasMore && (
                <button
                  className="inbox-section__load-more"
                  type="button"
                  disabled={section.isLoadingMore}
                  onClick={() => onLoadMore(section.key)}
                >
                  {section.isLoadingMore ? 'Loading...' : 'Load More'}
                </button>
              )}
            </div>
          )}
        </>
      )}
    </section>
  )
}

function MegaphoneIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4 13.5h3.4l9.1 4.3V5.2L7.4 9.5H4Z" />
      <path d="M7.4 13.5 8.7 20H11" />
      <path d="M19 9.2c1 .7 1.5 1.6 1.5 2.8s-.5 2.1-1.5 2.8" />
    </svg>
  )
}

export default InboxSection
