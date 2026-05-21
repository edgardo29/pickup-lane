import { Link } from 'react-router-dom'
import { UsersIcon } from '../../components/BrowseIcons.jsx'

export function BookingRulesCard({ policyUrl, rules }) {
  return (
    <section className="details-card details-rules">
      <div className="details-card__heading">
        <span className="details-section-icon">
          <RulesIcon />
        </span>
        <h2>Game Terms</h2>
      </div>

      <div className="details-rules__grid">
        {rules.map((rule) => (
          <Rule kind={rule.kind} title={rule.title} text={rule.text} key={rule.title} />
        ))}
      </div>

      {policyUrl && (
        <Link className="details-policy-link" to={policyUrl} state={{ from: window.location.pathname, fromLabel: 'Back to game' }}>
          View cancellation and refund policy
        </Link>
      )}
    </section>
  )
}

function Rule({ kind, title, text }) {
  return (
    <article className="details-rule">
      <div className="details-rule__icon">
        <RuleItemIcon kind={kind} />
      </div>

      <div>
        <h3>{title}</h3>
        <p>{text}</p>
      </div>
    </article>
  )
}

function RulesIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4 5h16" />
      <path d="M4 12h16" />
      <path d="M4 19h16" />
      <path d="M7 3v18" />
      <path d="M17 3v18" />
    </svg>
  )
}

function RuleItemIcon({ kind }) {
  if (kind === 'payment') {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <rect x="3.5" y="6" width="17" height="12" rx="2" />
        <path d="M3.5 10h17" />
        <path d="M7.5 15h3" />
      </svg>
    )
  }

  if (kind === 'weather') {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M7.5 16.5h9.2a4 4 0 0 0 .4-8 5.8 5.8 0 0 0-10.8 1.8A3.2 3.2 0 0 0 7.5 16.5Z" />
        <path d="m11 14-2 4h3l-1.5 3" />
      </svg>
    )
  }

  if (kind === 'age') {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <circle cx="12" cy="12" r="8.5" />
        <path d="M8.2 12h3" />
        <path d="M9.7 10.5v3" />
        <path d="M13.5 10.2h2.2v3.6" />
        <path d="M14 12h2" />
      </svg>
    )
  }

  if (kind === 'shield') {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M12 2.8 4.8 5.9v5.6c0 4.5 2.9 8.5 7.2 9.8 4.3-1.3 7.2-5.3 7.2-9.8V5.9L12 2.8Z" />
        <path d="m8.8 12.1 2.1 2.1 4.6-5" />
      </svg>
    )
  }

  if (kind === 'players') {
    return <UsersIcon />
  }

  if (kind === 'rules') {
    return <RulesIcon />
  }

  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 7.5V12l3.2 2" />
    </svg>
  )
}
