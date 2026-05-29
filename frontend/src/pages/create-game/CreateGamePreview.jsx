import { Link } from 'react-router-dom'
import { ShieldCheckIcon as SuccessShieldIcon } from '../../components/AuthIcons.jsx'
import {
  BuildingIcon,
  CalendarIcon,
  ChatIcon,
  ClipboardListIcon,
  ClockIcon,
  MapPinIcon,
  UsersIcon,
} from '../../components/BrowseIcons.jsx'
import BrowseAppNav from '../../components/BrowseAppNav.jsx'
import {
  buildPreviewLocation,
  capitalize,
  formatMoney,
} from './createGameFormatters.js'

export function CreateGamePreview({ form, review }) {
  const previewTitle = form.venueName ? `${form.venueName} ${form.format}` : `Community ${form.format}`

  return (
    <aside className="create-game-preview" aria-label="Game preview">
      <div className="create-game-preview__header">
        <span>Live preview</span>
        <strong title={previewTitle}>{previewTitle}</strong>
      </div>

      <div className="create-game-preview__facts">
        <PreviewFact icon={<CalendarIcon />} label={review.date} />
        <PreviewFact icon={<ClockIcon />} label={review.time} />
        <PreviewFact icon={<MapPinIcon />} label={buildPreviewLocation(form)} />
        <PreviewFact icon={<UsersIcon />} label={`${form.totalSpots} spots - ${form.format}`} />
        <PreviewFact icon={<BuildingIcon />} label={capitalize(form.environment)} />
      </div>

      <div className="create-game-preview__notes">
        <PreviewNote
          icon={<ChatIcon />}
          label="Game notes"
          text={form.gameNotes || 'Add a note so players know what to bring.'}
        />
        {(form.hostRules || '').trim() && (
          <PreviewNote
            icon={<ClipboardListIcon />}
            label="Host rules"
            text={form.hostRules}
          />
        )}
      </div>

      <div className="create-game-preview__money">
        <span>Player price</span>
        <strong>{formatMoney(Number(form.price) * 100)}</strong>
      </div>
    </aside>
  )
}

export function PublishedState({ gameId }) {
  return (
    <div className="create-game-page">
      <BrowseAppNav />
      <main className="create-game-success">
        <div className="create-game-success__mark">
          <SuccessShieldIcon />
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

function PreviewNote({ icon, label, text }) {
  return (
    <div className="create-game-preview__note">
      {icon}
      <div>
        <strong>{label}</strong>
        <p>{text}</p>
      </div>
    </div>
  )
}

function PreviewFact({ icon, label }) {
  return (
    <span className="create-game-preview__fact">
      {icon}
      <span className="create-game-preview__fact-label">{label}</span>
    </span>
  )
}
