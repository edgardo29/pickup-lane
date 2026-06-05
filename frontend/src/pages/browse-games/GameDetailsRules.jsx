import { Link } from 'react-router-dom'
import {
  BadgeInfo,
  CircleDollarSign,
  ClipboardList,
  Clock3,
  CloudLightning,
  ListChecks,
  ShieldCheck,
  UsersRound,
} from 'lucide-react'

export function BookingRulesCard({ policyUrl, rules }) {
  return (
    <section className="details-card details-rules">
      <div className="details-card__heading">
        <span className="details-section-icon">
          <ListChecks />
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

function RuleItemIcon({ kind }) {
  const icons = {
    age: BadgeInfo,
    clock: Clock3,
    payment: CircleDollarSign,
    players: UsersRound,
    rules: ClipboardList,
    shield: ShieldCheck,
    weather: CloudLightning,
  }
  const Icon = icons[kind] || Clock3

  return <Icon />
}
