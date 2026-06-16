import { X } from 'lucide-react'
import { PlayersIcon } from '../../components/GameFactIcons.jsx'
import { getInitials } from './gameDetailsFormatters.js'
import { InfoCard } from './GameDetailsPrimitives.jsx'

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
      icon={<PlayersIcon />}
      title="Players"
      badge={isFull ? (
        <>
          <PlayersIcon />
          Full
        </>
      ) : ''}
      cta={cta}
      ctaDisabled={ctaDisabled}
      ctaIcon={<PlayersIcon />}
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
            <h2 className="details-player-modal__title" id="details-player-modal-title">
              <span>
                <PlayersIcon />
              </span>
              Players
            </h2>
            <p>
              {participantSummary.signedUpCount}/{participantSummary.totalSpots} joined ·{' '}
              {participantSummary.spotsLeft} spots left
            </p>
          </div>

          <button type="button" aria-label="Close player list" onClick={onClose}>
            <X aria-hidden="true" />
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
