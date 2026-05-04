import BrandMark from './BrandMark.jsx'
import { LockIcon, UserPlusIcon } from './LandingIcons.jsx'

function LandingAuthCard() {
  return (
    <section className="auth-card" aria-label="Get started">
      <BrandMark className="auth-card__brand" />

      <p className="auth-card__subtitle">Get started in seconds</p>

      <a className="auth-card__create" href="#create-account">
        <UserPlusIcon />
        Create Account
      </a>

      <a className="auth-card__signin" href="#signin">
        <LockIcon />
        Sign In
      </a>

      <p className="auth-card__secure-note">
        <LockIcon />
        <span>Your information is secure and will never be shared.</span>
      </p>
    </section>
  )
}

export default LandingAuthCard
