import { Link, useLocation } from 'react-router-dom'
import { ArrowLeftIcon } from '../components/AuthIcons.jsx'
import BrandMark from '../components/BrandMark.jsx'
import { LEGAL_POLICIES, LEGAL_POLICY_IDS } from '../features/legal/legalPolicies.js'
import '../styles/legal/LegalPages.css'

export function TermsPage() {
  return <LegalPage policy={LEGAL_POLICIES[LEGAL_POLICY_IDS.terms]} />
}

export function PrivacyPage() {
  return <LegalPage policy={LEGAL_POLICIES[LEGAL_POLICY_IDS.privacy]} />
}

export function CancellationRefundPolicyPage() {
  return <LegalPage policy={LEGAL_POLICIES[LEGAL_POLICY_IDS.cancellationRefunds]} />
}

function LegalPage({ policy }) {
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
          <Link className="legal-home app-back-control" to={from} aria-label={fromLabel}>
            <span className="app-back-control__icon">
              <ArrowLeftIcon />
            </span>
            <span>Back</span>
          </Link>
        </nav>

        <article className="legal-card">
          <p className="legal-kicker">{policy.eyebrow}</p>
          <h1>{policy.title}</h1>
          <div className="legal-content">
            {policy.sections.map((section) => (
              <LegalSection key={section.title} title={section.title}>
                {section.body}
              </LegalSection>
            ))}
          </div>
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
