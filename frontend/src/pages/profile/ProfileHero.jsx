import { Link } from 'react-router-dom'
import { CalendarIcon, MapPinIcon } from '../../components/BrowseIcons.jsx'
import { InitialsAvatar } from './ProfileAvatar.jsx'
import { GearIcon, PencilIcon } from './ProfileIcons.jsx'
import { formatLocation, formatMemberSince, getFullName } from './profileFormatters.js'

export function ProfileHero({ currentUser, settings }) {
  return (
    <section className="profile-hero-card">
      <InitialsAvatar user={currentUser} size="large" />

      <div className="profile-hero-card__body">
        <div className="profile-hero-card__top">
          <div>
            <p className="profile-kicker">Player Profile</p>
            <h1>{getFullName(currentUser)}</h1>
          </div>

          <Link className="profile-icon-button" to="/settings" aria-label="Open settings">
            <GearIcon />
          </Link>
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

        <Link
          className="profile-secondary-action"
          state={{ from: '/profile', fromLabel: 'Back to profile' }}
          to="/profile/edit"
        >
          <PencilIcon />
          Edit profile
        </Link>
      </div>
    </section>
  )
}
