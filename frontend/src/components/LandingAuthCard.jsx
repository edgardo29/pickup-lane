import { Link } from 'react-router-dom'
import BrandMark from './BrandMark.jsx'
import { LockIcon, UserPlusIcon } from './LandingIcons.jsx'

function LandingAuthCard() {
  return (
    <section className="auth-card" aria-label="Get started">
      <BrandMark className="auth-card__brand" />

      <p className="auth-card__subtitle">Get started in seconds</p>

      <Link className="auth-card__create" to="/create-account">
        <UserPlusIcon />
        Create Account
      </Link>

      <Link className="auth-card__signin" to="/sign-in">
        <LockIcon />
        Sign In
      </Link>

      <p className="auth-card__secure-note">
        <LockIcon />
        <span>Your information is secure and will never be shared.</span>
      </p>
    </section>
  )
}

export default LandingAuthCard
