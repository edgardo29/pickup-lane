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

export function BookingRulesCard({ onOpenPolicy, rules }) {
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
          <Rule
            actionLabel={rule.actionLabel}
            kind={rule.kind}
            key={rule.title}
            onOpenPolicy={onOpenPolicy}
            policyId={rule.policyId}
            title={rule.title}
            text={rule.text}
          />
        ))}
      </div>
    </section>
  )
}

function Rule({ actionLabel, kind, onOpenPolicy, policyId, title, text }) {
  return (
    <article className="details-rule">
      <div className="details-rule__icon">
        <RuleItemIcon kind={kind} />
      </div>

      <div className="details-rule__content">
        <h3>{title}</h3>
        <p>{text}</p>
        {actionLabel && policyId && onOpenPolicy && (
          <button
            className="details-rule__policy-link"
            type="button"
            onClick={() => onOpenPolicy(policyId)}
          >
            {actionLabel}
          </button>
        )}
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
    conduct: ShieldCheck,
    shield: ShieldCheck,
    weather: CloudLightning,
  }
  const Icon = icons[kind] || Clock3

  return <Icon />
}
