import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  BuildingIcon,
  CalendarIcon,
  CheckIcon,
  ChatIcon,
  ClockIcon,
  CopyIcon,
  MapPinIcon,
  PencilIcon,
  PlusCircleIcon,
  PriceTagIcon,
  ShareIcon,
  ShieldCheckIcon,
  TrashIcon,
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

      <Fact
        icon={<PriceTagIcon />}
        label={(
          <>
            <strong>{price}</strong> per player
          </>
        )}
      />
    </section>
  )
}

export function PlayersCard({
  cta = 'View player list',
  ctaDisabled = false,
  disabledReason = '',
  onOpenPlayerList,
  participantSummary,
}) {
  const spotsLabel = participantSummary.spotsLeft === 1 ? 'spot left' : 'spots left'
  const isFull = participantSummary.spotsLeft <= 0

  return (
    <InfoCard
      className="details-info-card--players"
      icon={<UsersIcon />}
      title="Players"
      badge={isFull ? (
        <>
          <UsersIcon />
          Full
        </>
      ) : ''}
      cta={cta}
      ctaDisabled={ctaDisabled}
      ctaIcon={<UsersIcon />}
      eyebrow={disabledReason}
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
  hasUnread,
  latestChatMessage,
  messageCount = 0,
  onOpenChat,
  senderNames,
}) {
  const body = latestChatMessage?.message_body || 'No messages yet.'
  const senderLabel = getMessageSenderLabel(latestChatMessage, senderNames)

  return (
    <InfoCard
      className={[
        'details-info-card--chat',
        hasUnread ? 'details-info-card--unread' : '',
        !canOpenChat ? 'details-info-card--disabled' : '',
      ].filter(Boolean).join(' ')}
      icon={<ChatIconWithDot active={hasUnread} />}
      title="Game Chat"
      badge={hasUnread && canOpenChat ? 'New' : ''}
      eyebrow=""
      cta="Open chat"
      ctaDisabled={!canOpenChat}
      ctaIcon={<ChatIcon />}
      onCtaClick={onOpenChat}
    >
      <div className="details-chat-card__pills">
        <span className="details-stat-pill">
          <strong>{messageCount}</strong> {messageCount === 1 ? 'message' : 'messages'}
        </span>
      </div>
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

export function BookingRulesCard({ policyUrl, rules }) {
  return (
    <section className="details-card details-rules">
      <div className="details-card__heading">
        <span className="details-section-icon">
          <RulesIcon />
        </span>
        <h2>Game Terms</h2>
      </div>

      <div className="details-rules__grid">
        {rules.map((rule) => (
          <Rule kind={rule.kind} title={rule.title} text={rule.text} key={rule.title} />
        ))}
      </div>

      {policyUrl && (
        <Link className="details-policy-link" to={policyUrl} state={{ from: window.location.pathname, fromLabel: 'Back to game' }}>
          View cancellation and refund policy
        </Link>
      )}
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
  cancelGameDisabled = false,
  editGameUrl,
  editGameDisabled = false,
  facts,
  gameToneLabel,
  hostPaymentMethods = [],
  hostGuestCount,
  hostGuestMax,
  isAddingHostGuest,
  isCancellingGame,
  isUpdatingHostGuests,
  joinDisabled,
  joinLabel,
  joinMessage,
  joinNotice,
  leaveLabel,
  manageHostGuestsDisabled = false,
  onJoin,
  onCancelGame,
  onLeave,
  onManageHostGuests,
  onShare,
  price,
  returnPath,
  shareCopied,
  shareDisabled = false,
}) {
  return (
    <div className="details-booking-card">
      <div className="details-booking-card__price">
        <strong>{price}</strong>
        <span>per player</span>
      </div>

      {['Hosting', 'Joined', 'Waitlisted', 'Cancelled'].includes(joinLabel) ? (
        <div
          className={[
            'details-status-display',
            joinLabel === 'Joined' ? 'details-status-display--joined' : '',
            joinLabel === 'Waitlisted' ? 'details-status-display--waitlisted' : '',
            joinLabel === 'Cancelled' ? 'details-status-display--cancelled' : '',
          ].filter(Boolean).join(' ')}
          aria-label={`${joinLabel} status`}
        >
          {joinLabel === 'Cancelled' ? (
            <TrashIcon />
          ) : joinLabel === 'Joined' || joinLabel === 'Waitlisted' ? (
            <ShieldCheckIcon />
          ) : (
            <CalendarIcon />
          )}
          {joinLabel}
        </div>
      ) : (
        <button
          className="details-join-button"
          type="button"
          disabled={joinDisabled}
          onClick={onJoin}
        >
          {(joinLabel === 'Join Game' || joinLabel === 'Join Waitlist' || !joinLabel) && <PlusCircleIcon />}
          {joinLabel === 'Join Closed' && <ClockIcon />}
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
              to join this game.
            </>
          ) : (
            joinNotice
          )}
        </p>
      )}

      {editGameUrl && (
        editGameDisabled ? (
          <button className="details-secondary-action details-host-edit-action" type="button" disabled>
            <span className="details-action-icon">
              <PencilIcon />
            </span>
            <span>Edit Game</span>
            <span className="details-action-chevron" aria-hidden="true">›</span>
          </button>
        ) : (
          <Link className="details-secondary-action details-host-edit-action" to={editGameUrl}>
            <span className="details-action-icon">
              <PencilIcon />
            </span>
            <span>Edit Game</span>
            <span className="details-action-chevron" aria-hidden="true">›</span>
          </Link>
        )
      )}

      {onManageHostGuests && hostGuestMax > 0 && (
        <button
          className="details-secondary-action details-host-guest-action"
          type="button"
          disabled={manageHostGuestsDisabled || isAddingHostGuest || isUpdatingHostGuests}
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
        <button className="details-secondary-action" type="button" onClick={onLeave}>
          <span className="details-action-icon">
            <PencilIcon />
          </span>
          <span>{leaveLabel || 'Leave Game'}</span>
          <span className="details-action-chevron" aria-hidden="true">›</span>
        </button>
      )}

      {onCancelGame && (
        <button
          className="details-secondary-action details-cancel-game-action"
          type="button"
          disabled={cancelGameDisabled || isCancellingGame}
          onClick={onCancelGame}
        >
          <span className="details-action-icon">
            <TrashIcon />
          </span>
          <span>{isCancellingGame ? 'Cancelling...' : 'Cancel Game'}</span>
          <span className="details-action-chevron" aria-hidden="true">›</span>
        </button>
      )}

      <button
        className="details-secondary-action details-share-button"
        type="button"
        disabled={shareDisabled}
        onClick={onShare}
      >
        <span className="details-action-icon">
          <ShareIcon />
        </span>
        <span>Share Game</span>
        <span
          className={[
            'details-action-chevron',
            'details-share-indicator',
            shareCopied ? 'details-share-indicator--copied' : '',
          ].filter(Boolean).join(' ')}
          aria-hidden="true"
        >
          {shareCopied ? <CheckIcon /> : <CopyIcon />}
        </span>
      </button>

      <div className="details-sidebar-section">
        <h2>Quick Facts</h2>
        {facts.map((fact) => (
          <Fact icon={fact.icon} label={fact.label} key={fact.label} />
        ))}
        <Fact icon={<ShieldCheckIcon />} label={gameToneLabel} />
      </div>

      <div className="details-sidebar-section">
        <h2 className="details-section-heading">
          <span className="details-section-icon">
            <PencilIcon />
          </span>
          About This Game
        </h2>
        <p>{aboutText}</p>

        {hostPaymentMethods.length > 0 && (
          <HostPaymentSection methods={hostPaymentMethods} />
        )}
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

export function HostPaymentSection({ methods }) {
  if (!methods.length) {
    return null
  }

  return (
    <div className="details-host-payment-section">
      <div className="details-host-payment-list">
        {methods.map((method, index) => (
          <div className="details-host-payment-row" key={`${method.type}-${method.value}-${index}`}>
            <strong>{formatPaymentMethodType(method.type)}</strong>
            <span>{method.value}</span>
          </div>
        ))}
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
        <h2 id="host-guest-modal-title" className="details-confirm-modal__title">
          <span className="details-confirm-modal__title-icon">
            <UsersIcon />
          </span>
          Manage Guests
        </h2>

        <div className="details-attendance-actions details-host-guest-modal__body">
          <div className="details-attendance-actions__group details-attendance-actions__group--guests">
            <div>
              <strong>Guests</strong>
              <span>{nextGuestCount}/{guestMax} reserved for your game</span>
            </div>
            <div className="details-attendance-stepper" aria-label="Host guest count">
              <button
                type="button"
                aria-label="Remove one guest"
                disabled={!canDecrease || isSaving}
                onClick={() => changeGuestCount(-1)}
              >
                −
              </button>
              <span>{nextGuestCount}</span>
              <button
                type="button"
                aria-label="Add one guest"
                disabled={!canIncrease || isSaving}
                onClick={() => changeGuestCount(1)}
              >
                +
              </button>
            </div>
            <button type="submit" disabled={!hasChanges || isSaving}>
              {isSaving ? 'Saving...' : hasChanges ? 'Save Changes' : 'No Changes'}
            </button>
          </div>
        </div>

        {maxSelectableGuests < guestMax && (
          <p className="details-host-guest-modal__limit">
            Only {maxSelectableGuests} can be reserved right now.
          </p>
        )}

        <div className="details-confirm-modal__actions">
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

export function CancelGameModal({
  gameType,
  isCancelling,
  onClose,
  onConfirm,
}) {
  const isCommunityGame = gameType === 'community'

  return (
    <div className="details-modal-backdrop" role="presentation" onClick={onClose}>
      <section
        className="details-confirm-modal details-cancel-game-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="details-cancel-game-title"
        onClick={(event) => event.stopPropagation()}
      >
        <h2 id="details-cancel-game-title">Cancel game?</h2>
        <p>
          {isCommunityGame
            ? 'This will cancel the game for everyone and notify confirmed and waitlisted players.'
            : 'This will cancel the official game, notify players, and mark app payments for refund.'}
        </p>
        <div className="details-confirm-modal__actions">
          <button type="button" disabled={isCancelling} onClick={onClose}>
            Keep Game
          </button>
          <button className="danger" type="button" disabled={isCancelling} onClick={onConfirm}>
            {isCancelling ? 'Cancelling...' : 'Cancel Game'}
          </button>
        </div>
      </section>
    </div>
  )
}

export function LeaveGameModal({
  addableGuestCount = 0,
  canAddGuests = false,
  guestCount,
  guestMax = 0,
  isLeaving,
  isUpdatingGuests,
  isWaitlisted,
  onAddGuests,
  onClose,
  onConfirm,
  onRemoveGuests,
}) {
  const [nextGuestCount, setNextGuestCount] = useState(guestCount)
  const title = isWaitlisted ? 'Edit waitlist?' : 'Edit attendance?'
  const maxSelectableGuests = Math.min(guestMax, guestCount + addableGuestCount)
  const canDecreaseGuests = nextGuestCount > 0
  const canIncreaseGuests = nextGuestCount < maxSelectableGuests
  const guestDelta = nextGuestCount - guestCount
  const hasGuestChanges = guestDelta !== 0
  const guestActionLabel = guestDelta > 0
    ? 'Continue to Checkout'
    : guestDelta < 0
      ? isUpdatingGuests
        ? 'Updating...'
        : 'Update Guests'
      : 'No Changes'

  function changeGuestCount(delta) {
    setNextGuestCount((currentCount) => (
      Math.min(Math.max(currentCount + delta, 0), maxSelectableGuests)
    ))
  }

  function handleGuestUpdate() {
    if (!hasGuestChanges) {
      return
    }

    if (guestDelta > 0) {
      onAddGuests(guestDelta)
      return
    }

    onRemoveGuests(Math.abs(guestDelta))
  }

  return (
    <div className="details-modal-backdrop" role="presentation" onClick={onClose}>
      <section
        className="details-confirm-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="details-leave-title"
        onClick={(event) => event.stopPropagation()}
      >
        <h2 id="details-leave-title" className="details-confirm-modal__title">
          <span className="details-confirm-modal__title-icon">
            <UsersIcon />
          </span>
          {title}
        </h2>
        {isWaitlisted && <p>You will give up your waitlist position.</p>}
        {!isWaitlisted && (
          <div className="details-attendance-actions">
            {guestMax > 0 && (
              <div className="details-attendance-actions__group details-attendance-actions__group--guests">
                <div>
                  <strong>Guests</strong>
                  <span>{nextGuestCount}/{guestMax} on your booking</span>
                </div>
                <div className="details-attendance-stepper" aria-label="Guest count">
                  <button
                    type="button"
                    aria-label="Decrease guests"
                    disabled={!canDecreaseGuests || isLeaving || isUpdatingGuests}
                    onClick={() => changeGuestCount(-1)}
                  >
                    −
                  </button>
                  <span>{nextGuestCount}</span>
                  <button
                    type="button"
                    aria-label="Increase guests"
                    disabled={!canIncreaseGuests || isLeaving || isUpdatingGuests || (!canAddGuests && nextGuestCount >= guestCount)}
                    onClick={() => changeGuestCount(1)}
                  >
                    +
                  </button>
                </div>
                <button
                  type="button"
                  disabled={!hasGuestChanges || isLeaving || isUpdatingGuests}
                  onClick={handleGuestUpdate}
                >
                  {guestActionLabel}
                </button>
              </div>
            )}

            {guestMax <= 0 && guestCount > 0 && (
              <div className="details-attendance-actions__group">
                <strong>Guests</strong>
                <span>{guestCount} on your booking</span>
                <div className="details-attendance-actions__inline">
                  <button
                    type="button"
                    disabled={isLeaving || isUpdatingGuests}
                    onClick={() => onRemoveGuests(1)}
                  >
                    {isUpdatingGuests ? 'Updating...' : 'Remove 1 Guest'}
                  </button>
                </div>
              </div>
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

function formatPaymentMethodType(type) {
  const normalizedType = String(type || '').trim().toLowerCase()

  if (normalizedType === 'venmo') {
    return 'Venmo'
  }

  if (normalizedType === 'zelle') {
    return 'Zelle'
  }

  if (normalizedType === 'cashapp') {
    return 'Cash App'
  }

  if (normalizedType === 'cash') {
    return 'Cash'
  }

  return normalizedType ? normalizedType.replace(/^\w/, (letter) => letter.toUpperCase()) : 'Payment'
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

  if (kind === 'players') {
    return <UsersIcon />
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
