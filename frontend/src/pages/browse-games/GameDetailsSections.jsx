import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  BuildingIcon,
  CalendarIcon,
  ChatIcon,
  MapPinIcon,
  PencilIcon,
  PlusCircleIcon,
  ShareIcon,
  ShieldCheckIcon,
  UsersIcon,
} from '../../components/BrowseIcons.jsx'
import BrowseAppNav from '../../components/BrowseAppNav.jsx'
import darkMapPreview from '../../assets/maps/dark-map-preview.png'

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

export function GameGallery({
  activeImageIndex,
  images,
  onNext,
  onPrevious,
  onSelectImage,
}) {
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
        <span aria-hidden="true">$</span>
        <strong>{price}</strong>
        <span>per player</span>
      </div>
    </section>
  )
}

export function PlayersCard({ cta = 'View player list', ctaDisabled = false, onOpenPlayerList, participantSummary }) {
  const spotsLabel = participantSummary.spotsLeft === 1 ? 'spot left' : 'spots left'

  return (
    <InfoCard
      className="details-info-card--players"
      icon={<UsersIcon />}
      title="Players"
      cta={cta}
      ctaDisabled={ctaDisabled}
      ctaIcon={<UsersIcon />}
      onCtaClick={onOpenPlayerList}
    >
      <p className="details-player-card__summary">
        <strong>
          {participantSummary.signedUpCount}/{participantSummary.totalSpots}
        </strong>{' '}
        players
      </p>

      <div className="details-player-card__pills">
        <span className="details-stat-pill">
          <strong>{participantSummary.spotsLeft}</strong> {spotsLabel}
        </span>
        <span className="details-stat-pill">
          <strong>{participantSummary.waitlistCount}</strong> waitlist
        </span>
      </div>

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
  canOpenChat,
  disabledReason,
  hasUnread,
  isChatEnabled,
  latestChatMessage,
  onOpenChat,
  senderNames,
}) {
  const body = latestChatMessage?.message_body || 'No messages yet.'
  const senderLabel = getMessageSenderLabel(latestChatMessage, senderNames)
  const eyebrow = isChatEnabled
    ? !canOpenChat
      ? disabledReason || 'Members only'
      : hasUnread
      ? 'New messages'
      : 'Chat available'
    : 'Chat disabled'

  return (
    <InfoCard
      className={[
        hasUnread ? 'details-info-card--unread' : '',
        !canOpenChat ? 'details-info-card--disabled' : '',
      ].filter(Boolean).join(' ')}
      icon={<ChatIconWithDot active={hasUnread} />}
      title="Game Chat"
      badge={hasUnread && canOpenChat ? 'New' : ''}
      eyebrow={eyebrow}
      cta="Open chat"
      ctaDisabled={!canOpenChat}
      ctaIcon={<ChatIcon />}
      onCtaClick={onOpenChat}
    >
      <div className="details-chat-preview">
        <span className="details-chat-preview__avatar">{getInitials(senderLabel)}</span>
        <div className="details-chat-preview__body">
          <div className="details-chat-preview__meta">
            <strong>{senderLabel}</strong>
            {latestChatMessage && <small>{formatRelativeTime(latestChatMessage.created_at)}</small>}
          </div>
          <p>{body}</p>
        </div>
      </div>
    </InfoCard>
  )
}

export function ChatPanel({
  currentUserId,
  currentUserName,
  draft,
  error,
  isSending,
  maxLength,
  messages,
  onChangeDraft,
  onClose,
  onSend,
  senderNames,
}) {
  const pinnedMessage = messages.find((message) => message.is_pinned)
  const remainingCharacters = maxLength - draft.length

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
            <h2 className="details-chat-title" id="details-chat-panel-title">
              <span>
                <ChatIcon />
              </span>
              Game Chat
            </h2>
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
          {messages.length > 0 ? (
            messages.map((message) => (
              <ChatMessageRow
                currentUserId={currentUserId}
                currentUserName={currentUserName}
                message={message}
                senderNames={senderNames}
                key={message.id}
              />
            ))
          ) : (
            <p className="details-chat-empty">No messages yet.</p>
          )}
        </div>

        <form className="details-chat-composer" onSubmit={onSend}>
          <label htmlFor="details-chat-message">Message</label>
          <textarea
            id="details-chat-message"
            maxLength={maxLength}
            placeholder="Type a message"
            rows={2}
            value={draft}
            onChange={(event) => onChangeDraft(event.target.value)}
          />
          <div className="details-chat-composer__footer">
            <span className={remainingCharacters < 30 ? 'warn' : ''}>
              {draft.length}/{maxLength}
            </span>
            <button type="submit" disabled={isSending || !draft.trim()}>
              {isSending ? 'Sending...' : 'Send'}
            </button>
          </div>
          {error && <p className="details-chat-error">{error}</p>}
        </form>
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

export function WhereToGoCard({
  address,
  mapsUrl,
  parkingNote,
  venueName,
  mapIcon,
}) {
  const notes = [parkingNote && { icon: <ParkingIcon />, label: 'Parking', text: parkingNote }].filter(Boolean)

  return (
    <section className="details-card details-location">
      <div className="details-location__header">
        <div className="details-location__title">
          <span className="details-location__icon">{mapIcon}</span>
          <h2>Where to Go</h2>
        </div>

        {mapsUrl && (
          <a
            className="details-secondary-action details-location__map-link"
            href={mapsUrl}
            target="_blank"
            rel="noreferrer"
          >
            <span className="details-action-icon">
              <MapPinIcon />
            </span>
            <span>Open in Maps</span>
            <span className="details-action-chevron" aria-hidden="true">›</span>
          </a>
        )}
      </div>

      <div className="details-location__rows">
        <div className="details-location__row details-location__row--venue">
          <span className="details-location__note-icon">
            <BuildingIcon />
          </span>
          <div>
            <strong>Venue</strong>
            <h3>{venueName}</h3>
            <p>{address}</p>
          </div>
        </div>
      </div>

      <div className="details-location__map-preview" role="img" aria-label={`Map preview for ${venueName}`}>
        <img src={darkMapPreview} alt="" />
      </div>

      {notes.length > 0 && (
        <div className={`details-location__notes details-location__notes--${notes.length}`}>
          {notes.map((note) => (
            <div className="details-location__note" key={note.label}>
              <span className="details-location__note-icon">{note.icon}</span>
              <div>
                <strong>{note.label}</strong>
                <p>{note.text}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}

function ParkingIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="m5.2 11 1.7-4.2A2 2 0 0 1 8.8 5.5h6.4a2 2 0 0 1 1.9 1.3L18.8 11" />
      <rect x="4" y="10" width="16" height="7" rx="2" />
      <path d="M6.5 17v1.5" />
      <path d="M17.5 17v1.5" />
      <path d="M7.5 13.5h.1" />
      <path d="M16.5 13.5h.1" />
    </svg>
  )
}

export function JoinCard({
  aboutText,
  editGameUrl,
  facts,
  gameToneLabel,
  hostGuestCount,
  hostGuestMax,
  isAddingHostGuest,
  isUpdatingHostGuests,
  joinDisabled,
  joinLabel,
  joinMessage,
  joinNotice,
  leaveLabel,
  onJoin,
  onLeave,
  onManageHostGuests,
  onShare,
  price,
  returnPath,
  shareNotice,
}) {
  return (
    <div className="details-booking-card">
      <div className="details-booking-card__price">
        <strong>{price}</strong>
        <span>per player</span>
      </div>

      {joinLabel === 'Hosting' ? (
        <div className="details-status-display" aria-label="Hosting status">
          <CalendarIcon />
          Hosting
        </div>
      ) : (
        <button
          className="details-join-button"
          type="button"
          disabled={joinDisabled}
          onClick={onJoin}
        >
          {(joinLabel === 'Join Game' || joinLabel === 'Join Waitlist' || !joinLabel) && <PlusCircleIcon />}
          {joinLabel || 'Join Game'}
        </button>
      )}

      {joinNotice && (
        <p className="details-join-notice">
          {joinNotice === joinMessage ? (
            <>
              <Link state={{ from: returnPath }} to="/create-account">
                Create Account
              </Link>{' '}
              or{' '}
              <Link state={{ from: returnPath }} to="/sign-in">
                Sign In
              </Link>{' '}
              to join.
            </>
          ) : (
            joinNotice
          )}
        </p>
      )}

      {editGameUrl && (
        <Link className="details-secondary-action details-host-edit-action" to={editGameUrl}>
          <span className="details-action-icon">
            <PencilIcon />
          </span>
          <span>Edit Game</span>
          <span className="details-action-chevron" aria-hidden="true">›</span>
        </Link>
      )}

      {onManageHostGuests && hostGuestMax > 0 && (
        <button
          className="details-secondary-action details-host-guest-action"
          type="button"
          disabled={isAddingHostGuest || isUpdatingHostGuests}
          onClick={onManageHostGuests}
        >
          <span className="details-action-icon">
            <UsersIcon />
          </span>
          <span>Manage Guests</span>
          <strong className="details-action-count">{hostGuestCount}/{hostGuestMax}</strong>
          <span className="details-action-chevron" aria-hidden="true">›</span>
        </button>
      )}

      {onLeave && (
        <button className="details-leave-button" type="button" onClick={onLeave}>
          {leaveLabel || 'Leave Game'}
        </button>
      )}

      <button className="details-secondary-action details-share-button" type="button" onClick={onShare}>
        <span className="details-action-icon">
          <ShareIcon />
        </span>
        <span>Share Game</span>
        <span className="details-action-chevron" aria-hidden="true">›</span>
      </button>

      {shareNotice && <p className="details-join-notice">{shareNotice}</p>}

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

export function HostGuestModal({
  addableCount,
  guestCount,
  guestMax,
  isAdding,
  isRemoving,
  onClose,
  onSave,
}) {
  const [nextGuestCount, setNextGuestCount] = useState(guestCount)
  const isSaving = isAdding || isRemoving
  const maxSelectableGuests = Math.min(guestMax, guestCount + addableCount)
  const canDecrease = nextGuestCount > 0
  const canIncrease = nextGuestCount < maxSelectableGuests
  const hasChanges = nextGuestCount !== guestCount

  function changeGuestCount(delta) {
    setNextGuestCount((currentCount) => (
      Math.min(Math.max(currentCount + delta, 0), maxSelectableGuests)
    ))
  }

  function handleSubmit(event) {
    event.preventDefault()

    if (!hasChanges) {
      onClose()
      return
    }

    onSave(nextGuestCount)
  }

  return (
    <div className="details-modal-backdrop" role="presentation" onClick={onClose}>
      <form
        className="details-confirm-modal details-host-guest-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="host-guest-modal-title"
        onClick={(event) => event.stopPropagation()}
        onSubmit={handleSubmit}
      >
        <div className="details-host-guest-modal__header">
          <span className="details-host-guest-modal__icon">
            <UsersIcon />
          </span>
          <div>
            <h2 id="host-guest-modal-title">Manage Guests</h2>
            <p>
              Choose how many guest spots you want reserved.
            </p>
          </div>
          <button
            className="details-host-guest-modal__close"
            type="button"
            aria-label="Close host guest manager"
            onClick={onClose}
          >
            ×
          </button>
        </div>

        <div className="details-host-guest-stepper" aria-label="Host guest count">
          <button
            type="button"
            aria-label="Remove one guest"
            disabled={!canDecrease || isSaving}
            onClick={() => changeGuestCount(-1)}
          >
            −
          </button>
          <div>
            <strong>{nextGuestCount}</strong>
            <span>of {guestMax}</span>
          </div>
          <button
            type="button"
            aria-label="Add one guest"
            disabled={!canIncrease || isSaving}
            onClick={() => changeGuestCount(1)}
          >
            +
          </button>
        </div>

        {maxSelectableGuests < guestMax && (
          <p className="details-host-guest-modal__limit">
            Only {maxSelectableGuests} can be reserved right now.
          </p>
        )}

        <div className="details-host-guest-modal__actions">
          <button
            type="button"
            disabled={isSaving}
            onClick={onClose}
          >
            Cancel
          </button>
          <button className="primary" type="submit" disabled={isSaving}>
            {isSaving ? 'Saving...' : hasChanges ? 'Save Changes' : 'Done'}
          </button>
        </div>
      </form>
    </div>
  )
}

export function LeaveGameModal({
  guestCount,
  isLeaving,
  isUpdatingGuests,
  isWaitlisted,
  onClose,
  onConfirm,
  onRemoveGuests,
  refundEligible,
}) {
  const title = isWaitlisted ? 'Edit waitlist?' : 'Edit attendance?'
  const message = isWaitlisted
    ? 'You will give up your waitlist position.'
    : refundEligible
      ? 'You are more than 24 hours from kickoff, so this cancellation is eligible for a refund.'
      : 'This game starts within 24 hours, so leaving now will not receive a refund.'

  return (
    <div className="details-modal-backdrop" role="presentation" onClick={onClose}>
      <section
        className="details-confirm-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="details-leave-title"
        onClick={(event) => event.stopPropagation()}
      >
        <h2 id="details-leave-title">{title}</h2>
        <p>{message}</p>
        {guestCount > 0 && (
          <div className="details-attendance-actions">
            <button
              type="button"
              disabled={isLeaving || isUpdatingGuests}
              onClick={() => onRemoveGuests(1)}
            >
              {isUpdatingGuests ? 'Updating...' : 'Remove 1 Guest'}
            </button>
            {guestCount > 1 && (
              <button
                type="button"
                disabled={isLeaving || isUpdatingGuests}
                onClick={() => onRemoveGuests(guestCount)}
              >
                Remove All Guests
              </button>
            )}
          </div>
        )}
        <div className="details-confirm-modal__actions">
          <button type="button" onClick={onClose}>
            Keep Spot
          </button>
          <button className="danger" type="button" disabled={isLeaving} onClick={onConfirm}>
            {isLeaving ? 'Leaving...' : isWaitlisted ? 'Leave Waitlist' : 'Leave Game'}
          </button>
        </div>
      </section>
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
                <div className="details-roster-player__name">
                  <strong>{player.display_name_snapshot}</strong>
                  {player.guest_count > 0 && (
                    <span className="details-guest-pill">
                      +{player.guest_count} {player.guest_count === 1 ? 'guest' : 'guests'}
                    </span>
                  )}
                </div>
                {formatParticipantLabel(player) && <small>{formatParticipantLabel(player)}</small>}
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
  ctaDisabled = false,
  icon,
  title,
  eyebrow,
  cta,
  ctaIcon,
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
          <button
            className="details-secondary-action details-text-button"
            type="button"
            disabled={ctaDisabled}
            onClick={onCtaClick}
          >
            {ctaIcon && <span className="details-action-icon">{ctaIcon}</span>}
            <span>{cta}</span>
            <span className="details-action-chevron" aria-hidden="true">›</span>
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

function ChatMessageRow({ currentUserId, currentUserName, message, senderNames }) {
  const senderLabel = getMessageSenderLabel(message, senderNames)
  const isSystem = message.message_type === 'system' || message.message_type === 'pinned_update'
  const isOwn = !isSystem && currentUserId && message.sender_user_id === currentUserId
  const avatarLabel = isOwn ? currentUserName || senderLabel : senderLabel

  return (
    <article
      className={[
        'details-chat-message',
        isSystem ? 'details-chat-message--system' : '',
        isOwn ? 'details-chat-message--own' : '',
      ].filter(Boolean).join(' ')}
    >
      <span>{getInitials(avatarLabel)}</span>
      <div>
        <header>
          <strong>{isOwn ? 'You' : senderLabel}</strong>
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

  if (player.participant_status === 'waitlisted') {
    return 'Waitlist'
  }

  return ''
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
