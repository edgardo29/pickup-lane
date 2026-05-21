import { Link } from 'react-router-dom'
import {
  CheckIcon,
  CopyIcon,
  PencilIcon,
  ShareIcon,
  TrashIcon,
  UsersIcon,
} from '../../components/BrowseIcons.jsx'

function GameDetailsMobileActions({
  canCancelGame,
  canEditGame,
  canShowCancelGame,
  canShowEditGame,
  currentGuestCount,
  currentParticipant,
  gameId,
  hostGuestMax,
  isAddingHostGuest,
  isCancellingGame,
  isHost,
  isJoinWindowClosed,
  isUpdatingGuests,
  mobileActionCount,
  onOpenCancelGameModal,
  onOpenHostGuestModal,
  onOpenLeaveModal,
  onShare,
  shareCopied,
  shareDisabled,
}) {
  return (
    <section
      className={[
        'details-card',
        'details-mobile-host-actions',
        mobileActionCount === 1 ? 'details-mobile-host-actions--single' : '',
      ].filter(Boolean).join(' ')}
    >
      {canShowEditGame && (
        canEditGame ? (
          <Link className="details-secondary-action details-host-edit-action" to={`/games/${gameId}/edit`}>
            <span className="details-action-icon">
              <PencilIcon />
            </span>
            <span>Edit Game</span>
            <span className="details-action-chevron" aria-hidden="true">›</span>
          </Link>
        ) : (
          <button
            className="details-secondary-action details-host-edit-action"
            type="button"
            disabled
          >
            <span className="details-action-icon">
              <PencilIcon />
            </span>
            <span>Edit Game</span>
            <span className="details-action-chevron" aria-hidden="true">›</span>
          </button>
        )
      )}

      {isHost && hostGuestMax > 0 && (
        <button
          className="details-secondary-action details-host-guest-action"
          type="button"
          disabled={isJoinWindowClosed || isAddingHostGuest || isUpdatingGuests}
          onClick={onOpenHostGuestModal}
        >
          <span className="details-action-icon">
            <UsersIcon />
          </span>
          <span>Manage Guests</span>
          <strong className="details-action-count">{currentGuestCount}/{hostGuestMax}</strong>
          <span className="details-action-chevron" aria-hidden="true">›</span>
        </button>
      )}

      {currentParticipant && !isHost && !isJoinWindowClosed && (
        <button
          className="details-secondary-action"
          type="button"
          onClick={onOpenLeaveModal}
        >
          <span className="details-action-icon">
            <PencilIcon />
          </span>
          <span>
            {currentParticipant.participant_status === 'waitlisted'
              ? 'Leave Waitlist'
              : 'Edit Attendance'}
          </span>
          <span className="details-action-chevron" aria-hidden="true">›</span>
        </button>
      )}

      {canShowCancelGame && (
        <button
          className="details-secondary-action details-cancel-game-action"
          type="button"
          disabled={!canCancelGame || isCancellingGame}
          onClick={onOpenCancelGameModal}
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
    </section>
  )
}

export default GameDetailsMobileActions
