import { Link } from 'react-router-dom'
import {
  CalendarDays as CalendarIcon,
  CirclePlus as PlusCircleIcon,
  Clock3 as ClockIcon,
  ShieldCheck as ShieldCheckIcon,
  Trash2 as TrashIcon,
} from 'lucide-react'

function GameDetailsMobileJoinBar({
  currentParticipant,
  gameId,
  guestJoinMessage,
  isCancelledGame,
  isClosedJoinStatus,
  isHost,
  isJoinDisabled,
  joinLabel,
  joinNotice,
  onJoin,
  price,
}) {
  return (
    <div
      className={[
        'details-mobile-join',
        isHost ? 'details-mobile-join--host' : '',
        !isHost && currentParticipant ? 'details-mobile-join--participant' : '',
      ].filter(Boolean).join(' ')}
    >
      {isHost ? (
        <>
          <div>
            <strong>{price}</strong>
            <span>per player</span>
          </div>

          <span
            className={[
              'details-mobile-status-pill',
              isCancelledGame ? 'details-mobile-status-pill--cancelled' : '',
            ].filter(Boolean).join(' ')}
          >
            {isCancelledGame ? <TrashIcon /> : <CalendarIcon />}
            {isCancelledGame ? 'Cancelled' : 'Hosting'}
          </span>
        </>
      ) : currentParticipant ? (
        <>
          <div>
            <strong>{price}</strong>
            <span>per player</span>
          </div>

          <span
            className={[
              'details-mobile-status-pill',
              isCancelledGame ? 'details-mobile-status-pill--cancelled' : '',
            ].filter(Boolean).join(' ')}
          >
            {isCancelledGame ? <TrashIcon /> : <ShieldCheckIcon />}
            {isCancelledGame
              ? 'Cancelled'
              : currentParticipant.participant_status === 'waitlisted'
                ? 'Waitlisted'
                : 'Joined'}
          </span>
        </>
      ) : (
        <>
          <div>
            <strong>{price}</strong>
            <span>per player</span>
          </div>

          {isClosedJoinStatus ? (
            <span
              className={[
                'details-mobile-status-pill',
                isCancelledGame
                  ? 'details-mobile-status-pill--cancelled'
                  : 'details-mobile-status-pill--closed',
              ].filter(Boolean).join(' ')}
            >
              {isCancelledGame ? (
                <TrashIcon />
              ) : joinLabel === 'Join Closed' ? (
                <ClockIcon />
              ) : (
                <ShieldCheckIcon />
              )}
              {joinLabel}
            </span>
          ) : (
            <button type="button" disabled={isJoinDisabled} onClick={onJoin}>
              {(joinLabel === 'Join Game' || joinLabel === 'Join Waitlist' || !joinLabel) && (
                <PlusCircleIcon />
              )}
              {joinLabel}
            </button>
          )}

          {joinNotice && (
            <p>
              {joinNotice === guestJoinMessage ? (
                <AuthJoinNotice gameId={gameId} />
              ) : (
                joinNotice
              )}
            </p>
          )}
        </>
      )}
    </div>
  )
}

function AuthJoinNotice({ gameId }) {
  const returnPath = `/games/${gameId}`

  return (
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
  )
}

export default GameDetailsMobileJoinBar
