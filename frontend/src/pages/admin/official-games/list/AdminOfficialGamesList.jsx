import { Link } from 'react-router-dom'
import { CalendarIcon, MapPinIcon, PriceTagIcon, UsersIcon } from '../../../../components/BrowseIcons.jsx'
import {
  formatAdminGameMoney,
  formatOfficialGameSchedule,
} from '../shared/adminOfficialGameForm.js'

function AdminOfficialGamesList({ games }) {
  if (!games.length) {
    return (
      <div className="admin-official-empty-state">
        <strong>No official games found</strong>
        <span>Use a different status filter or open Create Official Game.</span>
      </div>
    )
  }

  return (
    <div className="admin-official-list">
      {games.map((game) => (
        <Link className="admin-official-list-row" key={game.id} to={`/admin/official-games/${game.id}`}>
          <div className="admin-official-list-row__copy">
            <strong>{game.title}</strong>
            <span><CalendarIcon />{formatOfficialGameSchedule(game)}</span>
            <span><MapPinIcon />{game.venue_name_snapshot}</span>
          </div>
          <div className="admin-official-list-row__meta">
            <em>{game.game_status}</em>
            <span><UsersIcon />{game.total_spots}</span>
            <span><PriceTagIcon />{formatAdminGameMoney(game.price_per_player_cents, game.currency)}</span>
          </div>
        </Link>
      ))}
    </div>
  )
}

export default AdminOfficialGamesList
