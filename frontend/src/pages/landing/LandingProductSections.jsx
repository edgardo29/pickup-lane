import venueFieldImage from '../../assets/landing-page-img-2.webp'
import aerialFieldsImage from '../../assets/landing-page-img-3.webp'
import sidelineGearImage from '../../assets/landing-page-img-4.webp'
import fieldGateImage from '../../assets/landing-page-img-5.webp'
import {
  GameFormatIcon,
  GameNotesIcon,
  GameSpotsIcon,
  PlayersIcon,
} from '../../components/GameFactIcons.jsx'
import { hostFlowItems, subFlowItems, waysToPlay } from './landingData.js'

const LANDING_IMAGE_SIZE = {
  width: 1672,
  height: 941,
}

const playCards = [
  {
    ...waysToPlay[0],
    image: aerialFieldsImage,
    detail: 'Verified venue',
    stat: 'Open checkout',
  },
  {
    ...waysToPlay[1],
    image: venueFieldImage,
    detail: 'Player-hosted',
    stat: 'Roster tools',
  },
  {
    ...waysToPlay[2],
    image: fieldGateImage,
    detail: 'Specific spots',
    stat: 'Request review',
  },
]

const hostTools = [
  {
    label: 'Build the game',
    detail: 'Venue, time, format, price',
    icon: GameFormatIcon,
  },
  {
    label: 'Track spots',
    detail: 'Roster, guests, waitlist',
    icon: PlayersIcon,
  },
  {
    label: 'Keep updates close',
    detail: 'Game chat and notes',
    icon: GameNotesIcon,
  },
  {
    label: 'Fill gaps',
    detail: 'Need a Sub requests',
    icon: GameSpotsIcon,
  },
]

function LandingWaysToPlay() {
  return (
    <section className="landing-section landing-ways" aria-labelledby="landing-ways-title">
      <div className="landing-section__header landing-ways__header">
        <p className="landing-section__eyebrow">Ways to play</p>
        <h2 id="landing-ways-title">Three ways to get on the field.</h2>
        <p>
          Join a curated game, start your own, or help another player fill a spot. Each path
          keeps the important details visible before anyone commits.
        </p>
      </div>

      <div className="landing-play-lanes">
        {playCards.map((item) => {
          const Icon = item.icon

          return (
            <article className="landing-way-card" key={item.title}>
              <img
                src={item.image}
                alt=""
                width={LANDING_IMAGE_SIZE.width}
                height={LANDING_IMAGE_SIZE.height}
                loading="lazy"
                decoding="async"
              />
              <div className="landing-way-card__body">
                <div className="landing-way-card__topline">
                  <Icon aria-hidden="true" />
                  <span className="landing-way-card__eyebrow">{item.eyebrow}</span>
                </div>
                <h3>{item.title}</h3>
                <p>{item.description}</p>
                <div className="landing-way-card__meta">
                  <span>{item.detail}</span>
                  <strong>{item.stat}</strong>
                </div>
              </div>
            </article>
          )
        })}
      </div>
    </section>
  )
}

function LandingHostAndSub() {
  return (
    <section className="landing-section landing-flow" aria-labelledby="landing-flow-title">
      <div className="landing-flow__copy">
        <p className="landing-section__eyebrow">Run the game</p>
        <h2 id="landing-flow-title">Tools for hosts and roster gaps.</h2>
        <p>
          Hosts get structure for the parts that usually end up in texts, spreadsheets,
          payment links, and last-minute reminders.
        </p>
      </div>

      <div className="landing-host-console" aria-label="Host tools preview">
        <figure className="landing-host-console__image">
          <img
            src={sidelineGearImage}
            alt=""
            width={LANDING_IMAGE_SIZE.width}
            height={LANDING_IMAGE_SIZE.height}
            loading="lazy"
            decoding="async"
          />
        </figure>

        <div className="landing-host-console__tools">
          {hostTools.map((tool) => {
            const Icon = tool.icon

            return (
              <article className="landing-host-tool" key={tool.label}>
                <Icon aria-hidden="true" />
                <div>
                  <h3>{tool.label}</h3>
                  <p>{tool.detail}</p>
                </div>
              </article>
            )
          })}
        </div>

        <div className="landing-host-console__workspace">
          <div className="landing-flow__panels">
            <FlowPanel title="Hosting a game" items={hostFlowItems} />
            <FlowPanel title="Need a Sub" items={subFlowItems} />
          </div>
        </div>
      </div>
    </section>
  )
}

function FlowPanel({ title, items }) {
  return (
    <article className="landing-flow-card">
      <h3>{title}</h3>
      <ol>
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ol>
    </article>
  )
}

export { LandingHostAndSub, LandingWaysToPlay }
