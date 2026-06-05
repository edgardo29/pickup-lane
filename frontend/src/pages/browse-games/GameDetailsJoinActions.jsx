import { Link } from 'react-router-dom'
import {
  CalendarDays as CalendarIcon,
  CirclePlus as PlusCircleIcon,
  Clock3 as ClockIcon,
  Pencil as PencilIcon,
  Share2 as ShareIcon,
  ShieldCheck as ShieldCheckIcon,
  Trash2 as TrashIcon,
  UsersRound as UsersIcon,
} from 'lucide-react'

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
          </button>
        ) : (
          <Link className="details-secondary-action details-host-edit-action" to={editGameUrl}>
            <span className="details-action-icon">
              <PencilIcon />
            </span>
            <span>Edit Game</span>
          </Link>
        )
      )}

      {onManageHostGuests && hostGuestMax > 0 && (
        <button
          className="details-secondary-action details-host-guest-action"
          type="button"
          aria-label={`Manage Guests ${hostGuestCount}/${hostGuestMax}`}
          disabled={manageHostGuestsDisabled || isAddingHostGuest || isUpdatingHostGuests}
          onClick={onManageHostGuests}
        >
          <span className="details-action-icon">
            <UsersIcon />
          </span>
          <span>Manage Guests</span>
        </button>
      )}

      {onLeave && (
        <button className="details-secondary-action" type="button" onClick={onLeave}>
          <span className="details-action-icon">
            <PencilIcon />
          </span>
          <span>{leaveLabel || 'Leave Game'}</span>
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
        <span>{shareCopied ? 'Copied' : 'Share Game'}</span>
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
