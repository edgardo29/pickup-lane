import { Link } from 'react-router-dom'
import BrowseAppNav from '../components/BrowseAppNav.jsx'
import LandingAuthCard from '../components/LandingAuthCard.jsx'
import LandingFeatureBar from '../components/LandingFeatureBar.jsx'
import { ArrowRightIcon } from '../components/LandingIcons.jsx'
import SiteNav from '../components/SiteNav.jsx'
import { useAuth } from '../hooks/useAuth.js'
import '../styles/browse-games.css'
import '../styles/landing.css'

function LandingPage() {
  const { appUser, currentUser, isLoading } = useAuth()
  const showGuestActions = !isLoading && !appUser
  const showSignedInHome = !isLoading && appUser
  const firstName = getFirstName(appUser, currentUser)
  const heroClassName = [
    'landing-hero',
    showSignedInHome ? 'landing-hero--signed-in' : '',
    isLoading ? 'landing-hero--loading' : '',
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <div className="landing-page">
      {showSignedInHome || isLoading ? <BrowseAppNav isLoading={isLoading} /> : <SiteNav />}

      <main className={heroClassName}>
        <section className="landing-hero__copy">
          {showSignedInHome && (
            <p className="landing-hero__eyebrow">Welcome back{firstName ? `, ${firstName}` : ''}</p>
          )}

          <h1>
            Find and join pickup soccer games <span>near you.</span>
          </h1>

          <p>Book real games, meet real players, and play at approved venues near you.</p>

          {showGuestActions && (
            <Link className="landing-hero__cta" to="/games">
              Browse Games
              <ArrowRightIcon />
            </Link>
          )}
        </section>

        {showGuestActions && <LandingAuthCard />}
        {showSignedInHome && <SignedInHeroPanel />}
      </main>

      <LandingFeatureBar />
    </div>
  )
}

function SignedInHeroPanel() {
  return (
    <section className="signed-home-panel" aria-label="Pickup Lane actions">
      <h2>Ready to play?</h2>
      <p>Find an open game near you or create one for other players to join.</p>

      <div className="signed-home-panel__actions">
        <Link className="signed-home-panel__primary" to="/games">
          Browse Games
          <ArrowRightIcon />
        </Link>
        <Link className="signed-home-panel__secondary" to="/create-game">
          Create Game
        </Link>
      </div>
    </section>
  )
}

function getFirstName(appUser, firebaseUser) {
  if (appUser?.first_name) {
    return appUser.first_name
  }

  if (firebaseUser?.displayName) {
    return firebaseUser.displayName.trim().split(/\s+/)[0]
  }

  return ''
}

export default LandingPage
