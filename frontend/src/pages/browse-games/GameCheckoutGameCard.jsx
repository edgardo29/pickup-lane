import {
  CalendarIcon,
  ClockIcon,
  MapPinIcon,
  UsersIcon,
} from '../../components/BrowseIcons.jsx'
import {
  formatDate,
  formatTimeRange,
} from './browseGameFormatters.js'

export function GameCheckoutGameCard({ address, game, primaryImage, title }) {
  return (
    <section className="checkout-card checkout-game-card">
      <img src={primaryImage} alt="" />
      <div>
        <h2>{title}</h2>
        <p className="checkout-location">
          <MapPinIcon />
          <span>
            {game.venue_name_snapshot}
            <small>{address}</small>
          </span>
        </p>
        <div className="checkout-chips">
          <span>
            <CalendarIcon /> {formatDate(game.starts_at)}
          </span>
          <span>
            <ClockIcon /> {formatTimeRange(game.starts_at, game.ends_at, { separator: ' - ' })}
          </span>
          <span>
            <UsersIcon /> {game.format_label}
          </span>
        </div>
      </div>
    </section>
  )
}
