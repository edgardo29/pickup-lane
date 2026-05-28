import { CalendarIcon, MapPinIcon } from '../../components/BrowseIcons.jsx'
import { InitialsAvatar } from './ProfileAvatar.jsx'
import { GameCreditIcon, PencilIcon } from './ProfileIcons.jsx'
import {
  formatCreditAmount,
  formatLocation,
  formatMemberSince,
  getFullName,
} from './profileFormatters.js'

export function ProfileHero({
  currentUser,
  gameCreditBalance,
  onEditProfile,
  settings,
}) {
  return (
    <section className="profile-hero-card">
      <InitialsAvatar user={currentUser} size="large" />

      <div className="profile-hero-card__body">
        <div className="profile-hero-card__top">
          <div>
            <p className="profile-kicker">Player Profile</p>
            <h1>{getFullName(currentUser)}</h1>
          </div>
        </div>

        <div className="profile-meta">
          <span>
            <MapPinIcon />
            {formatLocation(currentUser, settings)}
          </span>
          <span>
            <CalendarIcon />
            Member since {formatMemberSince(currentUser.member_since)}
          </span>
        </div>

        <div className="profile-hero-actions">
          <button
            className="profile-secondary-action"
            onClick={onEditProfile}
            type="button"
          >
            <PencilIcon />
            Edit profile
          </button>
          <div className="profile-credit-pill" aria-label="Available game credits">
            <GameCreditIcon />
            <span>Credits</span>
            <strong>
              {formatCreditAmount(
                gameCreditBalance?.available_credit_cents,
                gameCreditBalance?.currency,
              )}
            </strong>
          </div>
        </div>
      </div>
    </section>
  )
}
