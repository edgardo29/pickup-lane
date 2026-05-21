import { Link } from 'react-router-dom'
import {
  CalendarIcon,
  CheckIcon,
  ClockIcon,
  CopyIcon,
  PencilIcon,
  PlusCircleIcon,
  ShareIcon,
  ShieldCheckIcon,
  TrashIcon,
  UsersIcon,
} from '../../components/BrowseIcons.jsx'

export function JoinActionStack({
  cancelGameDisabled = false,
  editGameDisabled = false,
  editGameUrl,
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
  onCancelGame,
  onJoin,
  onLeave,
  onManageHostGuests,
  onShare,
  returnPath,
  shareCopied,
  shareDisabled = false,
}) {
  return (
    <>
      {['Hosting', 'Joined', 'Waitlisted', 'Cancelled'].includes(joinLabel) ? (
        <JoinStatusDisplay joinLabel={joinLabel} />
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
    </>
  )
}

function JoinStatusDisplay({ joinLabel }) {
  return (
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
  )
}
