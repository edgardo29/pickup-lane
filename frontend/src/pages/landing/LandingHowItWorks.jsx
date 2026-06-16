import { howItWorksSteps } from './landingData.js'

function LandingHowItWorks() {
  return (
    <section className="landing-section landing-how" id="how-it-works" aria-labelledby="landing-how-title">
      <div className="landing-section__header">
        <p className="landing-section__eyebrow">How it works</p>
        <h2 id="landing-how-title">From finding a game to kickoff.</h2>
        <p>
          Pickup Lane keeps the whole run in one place: discovery, booking, roster updates,
          venue details, and game-day coordination.
        </p>
      </div>

      <div className="landing-how__path" aria-label="Pickup Lane booking steps">
        {howItWorksSteps.map((step) => {
          const Icon = step.icon

          return (
            <article className="landing-how-step" key={step.title}>
              <div className="landing-how-step__marker">
                <span>{step.metric}</span>
                <Icon aria-hidden="true" />
              </div>
              <div>
                <h3>{step.title}</h3>
                <p>{step.description}</p>
              </div>
            </article>
          )
        })}
      </div>
    </section>
  )
}

export default LandingHowItWorks
