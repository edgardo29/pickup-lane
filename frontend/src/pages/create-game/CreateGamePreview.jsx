import { Link } from 'react-router-dom'
import { ShieldCheckIcon } from '../../components/AuthIcons.jsx'
import {
  BuildingIcon,
  CalendarIcon,
  ClockIcon,
  MapPinIcon,
  UsersIcon,
} from '../../components/BrowseIcons.jsx'
import BrowseAppNav from '../../components/BrowseAppNav.jsx'
import {
  buildPreviewLocation,
  capitalize,
  COMMUNITY_PUBLISH_FEE_CENTS,
  formatMoney,
  formatPaymentMethod,
} from './createGameUtils.js'

export function CreateGamePreview({ firstPublishIsFree, form, paymentMethod, review }) {
  return (
    <aside className="create-game-preview" aria-label="Game preview">
      <div className="create-game-preview__header">
        <span>Live preview</span>
        <strong>{form.venueName ? `${form.venueName} ${form.format}` : `Community ${form.format}`}</strong>
      </div>

      <div className="create-game-preview__facts">
        <PreviewFact icon={<CalendarIcon />} label={review.date} />
        <PreviewFact icon={<ClockIcon />} label={review.time} />
        <PreviewFact icon={<MapPinIcon />} label={buildPreviewLocation(form)} />
        <PreviewFact icon={<UsersIcon />} label={`${form.totalSpots} spots - ${form.format}`} />
        <PreviewFact icon={<BuildingIcon />} label={capitalize(form.environment)} />
      </div>

      <div className="create-game-preview__money">
        <span>Player price</span>
        <strong>{formatMoney(Number(form.price) * 100)}</strong>
      </div>

      <div className="create-game-preview__money">
        <span>Publish fee</span>
        <strong>{firstPublishIsFree ? 'Free' : formatMoney(COMMUNITY_PUBLISH_FEE_CENTS)}</strong>
      </div>

      <p className="create-game-preview__note">
        {form.gameNotes || 'Add a note so players know what to bring.'}
      </p>

      <p className="create-game-preview__card">
        {firstPublishIsFree ? 'First community game fee waived' : `Paying with ${formatPaymentMethod(paymentMethod)}`}
      </p>
    </aside>
  )
}

export function PublishedState({ gameId }) {
  return (
    <div className="create-game-page">
      <BrowseAppNav />
      <main className="create-game-success">
        <div className="create-game-success__mark">
          <ShieldCheckIcon />
        </div>
        <h1>Game Published!</h1>
        <p>Your community game is now live and visible to players.</p>
        <Link className="create-game-primary" to={`/games/${gameId}`}>
          View Game
          <span aria-hidden="true">→</span>
        </Link>
      </main>
    </div>
  )
}

function PreviewFact({ icon, label }) {
  return (
    <span>
      {icon}
      {label}
    </span>
  )
}
