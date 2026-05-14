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
    <section className="feature-bar" id="how-it-works" aria-label="Pickup Lane benefits">
      <h2 className="feature-bar__heading">
        Why <span>Pickup</span> Lane?
      </h2>

      <div className="feature-bar__grid">
        {features.map((feature) => {
          const Icon = feature.icon

          return (
            <article className="feature-item" key={feature.title}>
              <div className="feature-item__icon">
                <Icon />
              </div>
              <div>
                <h3>{feature.title}</h3>
                <p>{feature.description}</p>
              </div>
            </article>
          )
        })}
      </div>
    </section>
  )
}

export default LandingFeatureBar
