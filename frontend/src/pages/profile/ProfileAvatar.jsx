import { getInitials } from './profileFormatters.js'

export function InitialsAvatar({ user, size = 'default' }) {
  return (
    <div className={`profile-avatar profile-avatar--${size}`} aria-hidden="true">
      {getInitials(user)}
    </div>
  )
}
