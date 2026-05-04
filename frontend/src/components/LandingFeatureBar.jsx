import { MapPinIcon, ShieldCheckIcon, UsersIcon } from './LandingIcons.jsx'

const features = [
  {
    title: 'Official Games',
    description: 'Curated by our team at approved venues.',
    icon: ShieldCheckIcon,
  },
  {
    title: 'Community Hosted',
    description: 'Player-created pickup games.',
    icon: UsersIcon,
  },
  {
    title: 'Approved Venues',
    description: 'Real fields, no random park confusion.',
    icon: MapPinIcon,
  },
]

function LandingFeatureBar() {
  return (
    <section className="feature-bar" aria-label="Pickup Lane benefits">
      {features.map((feature) => {
        const Icon = feature.icon

        return (
          <article className="feature-item" key={feature.title}>
            <div className="feature-item__icon">
              <Icon />
            </div>
            <div>
              <h2>{feature.title}</h2>
              <p>{feature.description}</p>
            </div>
          </article>
        )
      })}
    </section>
  )
}

export default LandingFeatureBar
