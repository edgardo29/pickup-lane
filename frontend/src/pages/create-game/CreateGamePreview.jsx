import { Link } from 'react-router-dom'
import { ShieldCheckIcon as SuccessShieldIcon } from '../../components/AuthIcons.jsx'
import {
  AddressIcon,
  GameDateIcon,
  GameNotesIcon,
  GameTimeIcon,
  HostRulesIcon,
} from '../../components/GameFactIcons.jsx'
import BrowseAppNav from '../../components/BrowseAppNav.jsx'
import {
  buildPreviewLocation,
  capitalize,
  formatGamePlayerGroup,
  formatMoney,
  formatSkillLevel,
} from './createGameFormatters.js'

export function CreateGamePreview({ form, review }) {
  const previewTitle = form.venueName ? form.venueName : 'Community Game'

  return (
    <aside className="create-game-preview" aria-label="Game preview">
      <div className="create-game-preview__header">
        <span>Live preview</span>
        <strong title={previewTitle}>{previewTitle}</strong>
      </div>

      <PreviewSection title="Game">
        <PreviewFact icon={<GameDateIcon />} label={review.date} />
        <PreviewFact icon={<GameTimeIcon />} label={review.time} />
        <PreviewFact label={form.format || '-'} variant="dot" />
        <PreviewFact label={form.gamePlayerGroup ? formatGamePlayerGroup(form.gamePlayerGroup) : '-'} variant="dot" />
        <PreviewFact label={form.skillLevel ? formatSkillLevel(form.skillLevel) : '-'} variant="dot" />
        <PreviewFact label={form.environment ? capitalize(form.environment) : '-'} variant="dot" />
        <PreviewFact label={form.totalSpots ? `${form.totalSpots} spots` : '-'} variant="dot" />
      </PreviewSection>

      <PreviewSection title="Location">
        <PreviewFact icon={<AddressIcon />} label={formatPreviewLocation(form)} multiline />
      </PreviewSection>

      <PreviewSection title="Notes & Payment">
        <PreviewNote
          icon={<GameNotesIcon />}
          label="Game notes"
          text={form.gameNotes || 'Add a note so players know what to bring.'}
        />
        <PreviewNote
          icon={<HostRulesIcon />}
          label="Host rules"
          text={form.hostRules || 'Add host rules for players.'}
        />
        <PreviewMoney label="Player price" value={formatMoney(Number(form.price) * 100)} />
      </PreviewSection>
    </aside>
  )
}

function formatPreviewLocation(form) {
  const location = buildPreviewLocation(form)
  return location === 'Address not set' ? '-' : location
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

function PreviewSection({ children, title }) {
  return (
    <section className="create-game-preview__section">
      <span className="create-game-preview__section-title">{title}</span>
      {children}
    </section>
  )
}

function PreviewMoney({ label, value }) {
  return (
    <div className="create-game-preview__money">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

function PreviewFact({ icon = null, label, multiline = false, variant = '' }) {
  const className = [
    'create-game-preview__fact',
    multiline ? 'create-game-preview__fact--multiline' : '',
    variant ? `create-game-preview__fact--${variant}` : '',
  ].filter(Boolean).join(' ')

  return (
    <span className={className}>
      {icon}
      <span className="create-game-preview__fact-label">{label}</span>
    </span>
  )
}
