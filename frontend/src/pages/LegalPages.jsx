import { Link, useLocation } from 'react-router-dom'
import BrandMark from '../components/BrandMark.jsx'
import '../styles/legal.css'

export function TermsPage() {
  return (
    <LegalShell title="Terms of Service" eyebrow="Legal">
      <LegalSection title="Using Pickup Lane">
        Pickup Lane helps players find, join, host, and manage pickup soccer games.
        You are responsible for showing up on time, respecting other players, and
        following venue rules.
      </LegalSection>
      <LegalSection title="Games and payments">
        Game details, prices, cancellation rules, and host responsibilities may vary
        by game. Payments, credits, refunds, and deposits will follow the rules shown
        before checkout or publishing.
      </LegalSection>
      <LegalSection title="Account behavior">
        We may restrict or remove accounts that abuse the platform, repeatedly no-show,
        create unsafe games, or violate community expectations.
      </LegalSection>
      <LegalSection title="Placeholder notice">
        These terms are a working product placeholder while Pickup Lane is in
        development. Final legal language should be reviewed before launch.
      </LegalSection>
    </LegalShell>
  )
}

export function PrivacyPage() {
  return (
    <LegalShell title="Privacy Policy" eyebrow="Privacy">
      <LegalSection title="Information we collect">
        We collect account details, game activity, profile information, and settings
        needed to run Pickup Lane. Payment details should be handled by our payment
        provider, not stored directly by Pickup Lane.
      </LegalSection>
      <LegalSection title="How we use it">
        We use your information to authenticate your account, show relevant games,
        manage bookings, send account and game updates, and keep the platform safe.
      </LegalSection>
      <LegalSection title="Account deletion">
        If you delete your account, we remove your sign-in access and anonymize or
        delete personal profile details while keeping limited records needed for
        payments, disputes, security, or game history.
      </LegalSection>
      <LegalSection title="Placeholder notice">
        This privacy policy is a working product placeholder while Pickup Lane is in
        development. Final legal language should be reviewed before launch.
      </LegalSection>
    </LegalShell>
  )
}

function LegalShell({ children, eyebrow, title }) {
  const location = useLocation()
  const from = location.state?.from || '/'
  const fromLabel = location.state?.fromLabel || 'Back home'

  return (
    <main className="legal-page">
      <div className="legal-shell">
        <nav className="legal-nav" aria-label="Legal navigation">
          <Link className="legal-brand" to="/" aria-label="Pickup Lane home">
            <BrandMark compact />
          </Link>
          <Link className="legal-home" to={from}>
            {fromLabel}
          </Link>
        </nav>

        <article className="legal-card">
          <p className="legal-kicker">{eyebrow}</p>
          <h1>{title}</h1>
          <div className="legal-content">{children}</div>
        </article>
      </div>
    </main>
  )
}

function LegalSection({ children, title }) {
  return (
    <section>
      <h2>{title}</h2>
      <p>{children}</p>
    </section>
  )
}
