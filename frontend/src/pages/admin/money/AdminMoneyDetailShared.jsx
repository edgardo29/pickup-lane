import { Link } from 'react-router-dom'
import {
  FileClock,
  ShieldCheck,
} from 'lucide-react'
import {
  formatDateTime,
  formatMoney,
  formatStatus,
  shortId,
} from './adminMoneyFormatters.js'
import { getUserName } from './adminMoneySectionSelectors.js'

export function DetailField({ label, value }) {
  return (
    <div className="admin-money-field">
      <span>{label}</span>
      <strong>{value || 'None'}</strong>
    </div>
  )
}
export function DetailCodeField({ label, value }) {
  return (
    <div className="admin-money-field">
      <span>{label}</span>
      <code>{value || 'None'}</code>
    </div>
  )
}
export function SectionHeader({ count, icon: Icon, meta, title }) {
  const headerMeta = meta || (count !== undefined ? String(count) : '')

  return (
    <div className="admin-money-panel__heading">
      <div>
        <Icon />
        <h2>{title}</h2>
      </div>
      {headerMeta && <span className="admin-money-panel__meta">{headerMeta}</span>}
    </div>
  )
}
export function EmptyState({ children }) {
  return <p className="admin-money-empty">{children}</p>
}
export function ContextSection({
  booking,
  communityPublishAttempt,
  game,
  hostPublishFee,
  participant,
  publishHost,
  userSummary,
}) {
  const canOpenOfficialGame = game?.game_type === 'official'
  if (
    !booking
    && !game
    && !hostPublishFee
    && !communityPublishAttempt
    && !participant
    && !publishHost
    && !userSummary
  ) {
    return null
  }

  return (
    <section className="admin-money-panel" aria-label="Money context">
      <SectionHeader icon={ShieldCheck} title="Context" />
      <div className="admin-money-context">
        {game && (
          <div>
            <h3>Game</h3>
            <>
              <strong>{game.title}</strong>
              <span>{game.venue_name_snapshot}</span>
              <span>{formatDateTime(game.starts_at)}</span>
              {canOpenOfficialGame ? (
                <Link to={`/admin/official-games/${game.id}`}>Open official game</Link>
              ) : (
                <span>{formatStatus(game.game_type)} game</span>
              )}
            </>
          </div>
        )}
        {booking && (
          <div>
            <h3>Booking</h3>
            <>
              <strong>{formatStatus(booking.booking_status)}</strong>
              <span>{formatStatus(booking.payment_status)}</span>
              <span>{booking.participant_count} players</span>
              <span>{formatMoney(booking.total_cents, booking.currency)}</span>
            </>
          </div>
        )}
        {participant && (
          <div>
            <h3>Participant</h3>
            <>
              <strong>{participant.display_name_snapshot}</strong>
              <span>{formatStatus(participant.participant_status)}</span>
              <span>{formatStatus(participant.participant_type)}</span>
              <span>{formatMoney(participant.price_cents, participant.currency)}</span>
            </>
          </div>
        )}
        {hostPublishFee && (
          <div>
            <h3>Publish Fee</h3>
            <>
              <strong>{formatMoney(hostPublishFee.amount_cents, hostPublishFee.currency)}</strong>
              <span>{formatStatus(hostPublishFee.fee_status)}</span>
              <span>{formatStatus(hostPublishFee.waiver_reason)}</span>
              <code>{shortId(hostPublishFee.id)}</code>
            </>
          </div>
        )}
        {communityPublishAttempt && (
          <div>
            <h3>Publish Attempt</h3>
            <>
              <strong>{formatStatus(communityPublishAttempt.attempt_status)}</strong>
              <span>{formatMoney(communityPublishAttempt.amount_cents, communityPublishAttempt.currency)}</span>
              <span>{communityPublishAttempt.starts_on_local || 'No start date'}</span>
              <code>{shortId(communityPublishAttempt.id)}</code>
            </>
          </div>
        )}
        {publishHost && (
          <div>
            <h3>Host</h3>
            <>
              <strong>{getUserName(publishHost)}</strong>
              <span>{publishHost.email || 'No email'}</span>
              <span>{formatStatus(publishHost.account_status)}</span>
              <Link to={`/admin/users/${publishHost.id}`}>Open user</Link>
            </>
          </div>
        )}
        {userSummary && (
          <div>
            <h3>User</h3>
            <>
              <strong>{getUserName(userSummary)}</strong>
              <span>{userSummary.email || 'No email'}</span>
              <span>{formatStatus(userSummary.account_status)}</span>
              <Link to={`/admin/users/${userSummary.id}`}>Open user</Link>
            </>
          </div>
        )}
      </div>
    </section>
  )
}
export function AuditSection({ auditActions }) {
  return (
    <section className="admin-money-panel" aria-label="Admin actions">
      <SectionHeader count={auditActions.length} icon={FileClock} title="Admin Actions" />
      {auditActions.length === 0 ? (
        <EmptyState>No directly relevant admin actions linked here.</EmptyState>
      ) : (
        <div className="admin-money-row-list">
          {auditActions.map((action) => (
            <div className="admin-money-row" key={action.id}>
              <div>
                <strong>{formatStatus(action.action_type)}</strong>
                <span>{action.reason || 'No reason recorded'}</span>
              </div>
              <div>
                <span>{formatDateTime(action.created_at)}</span>
                <code>{shortId(action.id)}</code>
              </div>
              <div>
                <span>Admin</span>
                <code>{shortId(action.admin_user_id)}</code>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
