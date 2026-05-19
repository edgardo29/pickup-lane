import { ChatIcon } from '../../components/BrowseIcons.jsx'
import InboxRow from './InboxRow.jsx'

function InboxSection({ gamesById, items, onOpenNotification, section }) {
  if (items.length === 0) {
    return null
  }

  return (
    <section className="inbox-section">
      <div className="inbox-section__heading">
        {section.key === 'game' ? <ChatIcon /> : <MegaphoneIcon />}
        <div>
          <h2>{section.title}</h2>
          <p>{section.description}</p>
        </div>
      </div>

      <div className="inbox-list">
        {items.map((notification) => (
          <InboxRow
            game={gamesById.get(notification.related_game_id)}
            key={notification.id}
            notification={notification}
            onOpenNotification={onOpenNotification}
          />
        ))}
      </div>
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
