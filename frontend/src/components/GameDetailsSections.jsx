import {
  ChatIcon,
  ShieldCheckIcon,
  UsersIcon,
} from './BrowseIcons.jsx'
import BrowseAppNav from './BrowseAppNav.jsx'

export function DetailsScaffold({ state }) {
  return (
    <div className="details-page">
      <BrowseAppNav />
      <main className="details-shell">{state}</main>
    </div>
  )
}

export function StatusPill({ label }) {
  return (
    <div className="details-kicker">
      <ShieldCheckIcon />
      {label}
    </div>
  )
}

export function GameGallery({ activeImageIndex, images, onNext, onPrevious, onSelectImage }) {
  const activeImage = images[activeImageIndex]
  const hasMultipleImages = images.length > 1

  return (
    <section className="details-gallery" aria-label="Game photos">
      {activeImage ? (
        <img src={activeImage} alt="" />
      ) : (
        <div className="details-gallery__fallback">Pickup Lane</div>
      )}

      {hasMultipleImages && (
        <>
          <button
            className="details-gallery__arrow details-gallery__arrow--left"
            type="button"
            aria-label="Previous photo"
            onClick={onPrevious}
          >
            ‹
          </button>

          <button
            className="details-gallery__arrow details-gallery__arrow--right"
            type="button"
            aria-label="Next photo"
            onClick={onNext}
          >
            ›
          </button>

          <div className="details-gallery__dots" aria-label="Choose game photo">
            {images.map((image, index) => (
              <button
                className={index === activeImageIndex ? 'active' : ''}
                type="button"
                aria-label={`Show photo ${index + 1}`}
                onClick={() => onSelectImage(index)}
                key={`${image}-${index}`}
              />
            ))}
          </div>
        </>
      )}

      <span className="details-gallery__count">
        {Math.min(activeImageIndex + 1, Math.max(images.length, 1))} / {Math.max(images.length, 1)}
      </span>
    </section>
  )
}

export function QuickFacts({ facts, price, variant }) {
  const className =
    variant === 'mobile' ? 'details-mobile-facts' : 'details-facts details-facts--desktop'

  return (
    <section className={className} aria-label="Game facts">
      {facts.map((fact) => (
        <Fact icon={fact.icon} label={fact.label} key={fact.label} />
      ))}

      <div className="details-price-fact">
        <strong>{price}</strong>
        <span>per player</span>
      </div>
    </section>
  )
}

export function PlayersCard({ onOpenPlayerList, participantSummary }) {
  const spotsLabel = participantSummary.spotsLeft === 1 ? 'spot left' : 'spots left'
  const hostLabel = participantSummary.host ? 'Game day host' : ''

  return (
    <InfoCard
      icon={<UsersIcon />}
      title="Players"
      cta="View player list"
      onCtaClick={onOpenPlayerList}
    >
      <p className="details-player-card__summary">
        <strong>
          {participantSummary.signedUpCount}/{participantSummary.totalSpots}
        </strong>{' '}
        players
      </p>

      <p className="details-player-card__meta">
        <strong>{participantSummary.spotsLeft}</strong> {spotsLabel} ·{' '}
        <strong>{participantSummary.waitlistCount}</strong> waitlist
      </p>

      {participantSummary.host && (
        <div className="details-host-row">
          <span>{getInitials(participantSummary.host.display_name_snapshot)}</span>
          <p>
            <small>{hostLabel}</small>
            <strong>{participantSummary.host.display_name_snapshot}</strong>
          </p>
        </div>
      )}

      {participantSummary.roster.length > 0 && (
        <div className="details-avatars" aria-hidden="true">
          {participantSummary.roster.slice(0, 6).map((participant, index) => (
            <span
              className={participant.participant_type === 'host' ? 'details-avatar--host' : ''}
              key={participant.id || index}
            >
              {index === 5 && participantSummary.roster.length > 6
                ? `+${participantSummary.roster.length - 5}`
                : getInitials(participant.display_name_snapshot)}
            </span>
          ))}
        </div>
      )}
    </InfoCard>
  )
}

export function PlayersListModal({ activeTab, onClose, onSelectTab, participantSummary }) {
  const visiblePlayers =
    activeTab === 'waitlist' ? participantSummary.waitlist : participantSummary.roster
  const emptyText =
    activeTab === 'waitlist' ? 'No one is on the waitlist.' : 'No players have joined yet.'

  return (
    <div className="details-modal-backdrop" role="presentation" onClick={onClose}>
      <section
        className="details-player-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="details-player-modal-title"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="details-player-modal__header">
          <div>
            <h2 id="details-player-modal-title">Players</h2>
            <p>
              {participantSummary.signedUpCount}/{participantSummary.totalSpots} joined ·{' '}
              {participantSummary.spotsLeft} spots left
            </p>
          </div>

          <button type="button" aria-label="Close player list" onClick={onClose}>
            ×
          </button>
        </div>

        <div className="details-player-tabs" role="tablist" aria-label="Player list sections">
          <button
            className={activeTab === 'going' ? 'active' : ''}
            type="button"
            role="tab"
            aria-selected={activeTab === 'going'}
            onClick={() => onSelectTab('going')}
          >
            Going ({participantSummary.signedUpCount})
          </button>

          <button
            className={activeTab === 'waitlist' ? 'active' : ''}
            type="button"
            role="tab"
            aria-selected={activeTab === 'waitlist'}
            onClick={() => onSelectTab('waitlist')}
          >
            Waitlist ({participantSummary.waitlistCount})
          </button>
        </div>

        <RosterSection emptyText={emptyText} players={visiblePlayers} />
      </section>
    </div>
  )
}

export function GameChatCard({
  hasUnread,
  isChatEnabled,
  latestChatMessage,
  onOpenChat,
  senderNames,
}) {
  const body = latestChatMessage?.message_body || 'No messages yet.'
  const senderLabel = getMessageSenderLabel(latestChatMessage, senderNames)
  const eyebrow = isChatEnabled
    ? hasUnread
      ? 'New messages'
      : 'Chat available'
    : 'Chat disabled'

  return (
    <InfoCard
      className={hasUnread ? 'details-info-card--unread' : ''}
      icon={<ChatIconWithDot active={hasUnread} />}
      title="Game Chat"
      badge={hasUnread ? 'New' : ''}
      eyebrow={eyebrow}
      cta="Open chat"
      onCtaClick={onOpenChat}
    >
      <div className="details-chat-preview">
        <span>{getInitials(senderLabel)}</span>
        <p>
          <strong>{senderLabel}</strong>
          {latestChatMessage && <> · {formatRelativeTime(latestChatMessage.created_at)}</>}
          <br />
          {body}
        </p>
      </div>
    </InfoCard>
  )
}

export function ChatPanel({ messages, onClose, senderNames }) {
  const pinnedMessage = messages.find((message) => message.is_pinned)

  return (
    <div className="details-modal-backdrop" role="presentation" onClick={onClose}>
      <section
        className="details-chat-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="details-chat-panel-title"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="details-player-modal__header">
          <div>
            <h2 id="details-chat-panel-title">Game Chat</h2>
            <p>{messages.length > 0 ? 'Latest team updates' : 'No messages yet'}</p>
          </div>

          <button type="button" aria-label="Close chat" onClick={onClose}>
            ×
          </button>
        </div>

        {pinnedMessage && (
          <div className="details-chat-pinned">
            <strong>Pinned</strong>
            <p>{pinnedMessage.message_body}</p>
          </div>
        )}

        <div className="details-chat-thread">
          {messages.map((message) => (
            <ChatMessageRow message={message} senderNames={senderNames} key={message.id} />
          ))}
        </div>
      </section>
    </div>
  )
}

export function BookingRulesCard({ rules }) {
  return (
    <section className="details-card details-rules">
      <div className="details-card__heading">
        <RulesIcon />
        <h2>Booking & Rules</h2>
      </div>

      <div className="details-rules__grid">
        {rules.map((rule) => (
          <Rule kind={rule.kind} title={rule.title} text={rule.text} key={rule.title} />
        ))}
      </div>
    </section>
  )
}

export function WhereToGoCard({ address, arrivalText, mapsUrl, venueName, mapIcon }) {
  return (
    <section className="details-card details-location">
      <div className="details-card__heading">
        {mapIcon}
        <div>
          <h2>Where to Go</h2>
          <h3>{venueName}</h3>
          <p>{address}</p>
        </div>
      </div>

      <div className="details-map" role="img" aria-label={`Static map preview for ${venueName}`}>
        <span className="details-map__pin" />
      </div>

      <div className="details-location__notes">
        <p>{arrivalText}</p>
        {mapsUrl && (
          <a href={mapsUrl} target="_blank" rel="noreferrer">
            Open in Maps
          </a>
        )}
      </div>
    </section>
  )
}

export function JoinCard({
  aboutText,
  facts,
  gameToneLabel,
  joinMessage,
  joinNotice,
  onJoin,
  onShare,
  price,
}) {
  return (
    <div className="details-booking-card">
      <div className="details-booking-card__price">
        <strong>{price}</strong>
        <span>per player</span>
      </div>

      <button className="details-join-button" type="button" onClick={onJoin}>
        Join Game <span>›</span>
      </button>

      {joinNotice && <p className="details-join-notice">{joinMessage}</p>}

      <button className="details-share-button" type="button" onClick={onShare}>
        Share Game
      </button>

      <div className="details-sidebar-section">
        <h2>Quick Facts</h2>
        {facts.map((fact) => (
          <Fact icon={fact.icon} label={fact.label} key={fact.label} />
        ))}
        <Fact icon={<ShieldCheckIcon />} label={gameToneLabel} />
      </div>

      <div className="details-sidebar-section">
        <h2>About This Game</h2>
        <p>{aboutText}</p>
      </div>

      <div className="details-sidebar-section">
        <h2>Questions?</h2>
        <p>Check out our Help Center or contact our support team.</p>

        <a className="details-help-button" href="mailto:support@pickuplane.local">
          Visit Help Center
        </a>
      </div>
    </div>
  )
}

export function DetailsState({ title, message }) {
  return (
    <div className="details-state">
      <h1>{title}</h1>
      {message && <p>{message}</p>}
    </div>
  )
}

function Fact({ icon, label }) {
  return (
    <div className="details-fact">
      {icon}
      <span>{label}</span>
    </div>
  )
}

function RosterSection({ emptyText, players }) {
  return (
    <div className="details-roster-section">
      {players.length > 0 ? (
        <div className="details-roster-list">
          {players.map((player) => (
            <div className="details-roster-player" key={player.id}>
              <span>{getInitials(player.display_name_snapshot)}</span>
              <div>
                <strong>{player.display_name_snapshot}</strong>
                <small>{formatParticipantLabel(player)}</small>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="details-roster-empty">{emptyText}</p>
      )}
    </div>
  )
}

function InfoCard({
  badge = '',
  className = '',
  icon,
  title,
  eyebrow,
  cta,
  onCtaClick,
  rightArrow,
  children,
}) {
  return (
    <section className={`details-card details-info-card ${className}`.trim()}>
      <div className="details-info-card__icon">{icon}</div>

      <div className="details-info-card__body">
        <div className="details-info-card__title">
          <h2>{title}</h2>
          {badge && <span>{badge}</span>}
        </div>
        {eyebrow && <p className="details-eyebrow">{eyebrow}</p>}
        {children}
        {cta && (
          <button className="details-text-button" type="button" onClick={onCtaClick}>
            {cta}
          </button>
        )}
      </div>

      {rightArrow && onCtaClick && (
        <button
          className="details-card-arrow"
          type="button"
          aria-label={cta || title}
          onClick={onCtaClick}
        >
          ›
        </button>
      )}

      {rightArrow && !onCtaClick && <span className="details-card-arrow">›</span>}
    </section>
  )
}

function ChatIconWithDot({ active }) {
  return (
    <span className="details-chat-icon">
      <ChatIcon />
      {active && <i aria-hidden="true" />}
    </span>
  )
}

function ChatMessageRow({ message, senderNames }) {
  const senderLabel = getMessageSenderLabel(message, senderNames)
  const isSystem = message.message_type === 'system' || message.message_type === 'pinned_update'

  return (
    <article className={`details-chat-message ${isSystem ? 'details-chat-message--system' : ''}`}>
      <span>{getInitials(senderLabel)}</span>
      <div>
        <header>
          <strong>{senderLabel}</strong>
          <small>{formatRelativeTime(message.created_at)}</small>
        </header>
        <p>{message.message_body}</p>
      </div>
    </article>
  )
}

function getMessageSenderLabel(message, senderNames) {
  if (!message) {
    return 'Pickup Lane'
  }

  if (message.message_type === 'system' || message.message_type === 'pinned_update') {
    return 'Pickup Lane'
  }

  return senderNames.get(message.sender_user_id) || 'Game chat'
}

function formatParticipantLabel(player) {
  if (player.participant_type === 'host') {
    return 'Host'
  }

  if (player.participant_status === 'pending_payment') {
    return 'Pending payment'
  }

  return (
    player.participant_status.charAt(0).toUpperCase() +
    player.participant_status.slice(1).replaceAll('_', ' ')
  )
}

function Rule({ kind, title, text }) {
  return (
    <article className="details-rule">
      <div className="details-rule__icon">
        <RuleItemIcon kind={kind} />
      </div>

      <div>
        <h3>{title}</h3>
        <p>{text}</p>
      </div>
    </article>
  )
}

function getInitials(value) {
  if (!value) {
    return ''
  }

  return value
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase()
}

function formatRelativeTime(value) {
  if (!value) {
    return 'Just now'
  }

  const minutes = Math.max(1, Math.round((Date.now() - new Date(value)) / 60000))

  if (minutes < 60) {
    return `${minutes}m ago`
  }

  const hours = Math.round(minutes / 60)
  return `${hours}h ago`
}

function RulesIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4 5h16" />
      <path d="M4 12h16" />
      <path d="M4 19h16" />
      <path d="M7 3v18" />
      <path d="M17 3v18" />
    </svg>
  )
}

function RuleItemIcon({ kind }) {
  if (kind === 'payment') {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <rect x="3.5" y="6" width="17" height="12" rx="2" />
        <path d="M3.5 10h17" />
        <path d="M7.5 15h3" />
      </svg>
    )
  }

  if (kind === 'weather') {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M7.5 16.5h9.2a4 4 0 0 0 .4-8 5.8 5.8 0 0 0-10.8 1.8A3.2 3.2 0 0 0 7.5 16.5Z" />
        <path d="m11 14-2 4h3l-1.5 3" />
      </svg>
    )
  }

  if (kind === 'age') {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <circle cx="12" cy="12" r="8.5" />
        <path d="M8.2 12h3" />
        <path d="M9.7 10.5v3" />
        <path d="M13.5 10.2h2.2v3.6" />
        <path d="M14 12h2" />
      </svg>
    )
  }

  if (kind === 'shield') {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M12 2.8 4.8 5.9v5.6c0 4.5 2.9 8.5 7.2 9.8 4.3-1.3 7.2-5.3 7.2-9.8V5.9L12 2.8Z" />
        <path d="m8.8 12.1 2.1 2.1 4.6-5" />
      </svg>
    )
  }

  if (kind === 'rules') {
    return <RulesIcon />
  }

  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 7.5V12l3.2 2" />
    </svg>
  )
}
