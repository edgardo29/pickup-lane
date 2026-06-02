import { GameStatusIcon, PriceIcon } from '../../components/GameFactIcons.jsx'
import { Fact } from './GameDetailsPrimitives.jsx'

export function QuickFacts({ facts, price, variant }) {
  const className =
    variant === 'mobile' ? 'details-mobile-facts' : 'details-facts details-facts--desktop'

  return (
    <section className={className} aria-label="Game facts">
      {facts.map((fact, index) => (
        <Fact icon={fact.icon} label={fact.label} key={`${fact.label}-${index}`} />
      ))}

      <Fact
        icon={<PriceIcon />}
        label={(
          <>
            <strong>{price}</strong> per player
          </>
        )}
      />
    </section>
  )
}

export function SidebarQuickFacts({ facts, gameToneLabel }) {
  return (
    <div className="details-sidebar-section">
      <h2>Quick Facts</h2>
      {facts.map((fact, index) => (
        <Fact icon={fact.icon} label={fact.label} key={`${fact.label}-${index}`} />
      ))}
      <Fact icon={<GameStatusIcon />} label={gameToneLabel} />
    </div>
  )
}
