import {
  CalendarIcon,
  MapPinIcon,
  PriceTagIcon,
  UsersIcon,
} from '../../../../components/BrowseIcons.jsx'
import {
  formatAdminGameMoney,
  formatOfficialGameSchedule,
} from '../shared/adminOfficialGameForm.js'

function SummaryItem({ children, icon, label }) {
  return (
    <div className="admin-manage-summary__item">
      {icon}
      <span>{label}</span>
      <strong>{children}</strong>
    </div>
  )
}

function AdminOfficialGameSummary({ game, participants }) {
  const activeCount = participants.filter((participant) =>
    ['confirmed', 'pending_payment'].includes(participant.participant_status),
  ).length

  return (
    <section className="admin-manage-summary" aria-label="Official game summary">
      <div className="admin-manage-summary__title">
        <h2>{game.title}</h2>
        <em>{game.game_status}</em>
      </div>

      <div className="admin-manage-summary__grid">
        <SummaryItem icon={<CalendarIcon />} label="Schedule">
          {formatOfficialGameSchedule(game)}
        </SummaryItem>
        <SummaryItem icon={<MapPinIcon />} label="Venue">
          {game.venue_name_snapshot}
        </SummaryItem>
        <SummaryItem icon={<UsersIcon />} label="Roster">
          {activeCount} / {game.total_spots}
        </SummaryItem>
        <SummaryItem icon={<PriceTagIcon />} label="Price">
          {formatAdminGameMoney(game.price_per_player_cents, game.currency)}
        </SummaryItem>
      </div>
    </section>
  )
}

export default AdminOfficialGameSummary
