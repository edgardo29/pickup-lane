import { Link } from 'react-router-dom'
import LandingAuthCard from '../components/LandingAuthCard.jsx'
import LandingFeatureBar from '../components/LandingFeatureBar.jsx'
import { ArrowRightIcon } from '../components/LandingIcons.jsx'
import SiteNav from '../components/SiteNav.jsx'
import '../styles/landing.css'

function LandingPage() {
  return (
    <div className="landing-page">
      <SiteNav />

      <main className="landing-hero">
        <section className="landing-hero__copy">
          <h1>
            Find and join pickup soccer games <span>near you.</span>
          </h1>

          <p>Book real games, meet real players, and play at approved venues near you.</p>

          <Link className="landing-hero__cta" to="/games">
            Browse Games
            <ArrowRightIcon />
          </Link>
        </section>

        <LandingAuthCard />
      </main>

      <LandingFeatureBar />
    </div>
  )
}

export default LandingPage
