import { Link } from 'react-router-dom'
import BrandMark from './BrandMark.jsx'
import { LockIcon, UserPlusIcon } from './LandingIcons.jsx'
import { useAuth } from '../hooks/useAuth.js'

function LandingAuthCard({ showWhileLoading = false, variant = 'hero' }) {
  const { appUser, isLoading } = useAuth()

  if (appUser || (isLoading && !showWhileLoading)) {
    return null
  }

  if (variant === 'mobile') {
    return (
      <section className="auth-card auth-card--mobile" aria-label="Get started">
        <div className="auth-card__icon" aria-hidden="true">
          <UserPlusIcon />
        </div>

        <h2>
          Ready to <span>play?</span>
        </h2>
        <p className="auth-card__subtitle">Create your account in seconds.</p>

        <Link className="auth-card__create" to="/create-account">
          Create Account
          <span aria-hidden="true">→</span>
        </Link>

        <p className="auth-card__signin-copy">
          Already have an account? <Link to="/sign-in">Sign in</Link>
        </p>
      </section>
    )
  }

  return (
    <section className="auth-card auth-card--hero" aria-label="Get started">
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
