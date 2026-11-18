import { ShieldCheckIcon } from '../../components/BrowseIcons.jsx'
import {
  COMMUNITY_PAYMENT_RESPONSIBILITY_TEXT,
  getCommunityCancellationText,
} from './gamePolicyText.js'

const OFFICIAL_CANCELLATION_TEXT =
  'Cancel 24+ hours before game time to stay eligible for a refund or game credit; ' +
  'later cancellations may not be refunded. If Pickup Lane changes the game details ' +
  'after you book and they no longer work for you, you can ask to leave and choose a ' +
  'refund to your original payment method or game credit, even after that cutoff.'

export function GameCheckoutPolicyCard({ game }) {
  const isCommunityGame = game.game_type === 'community'

  return (
    <section className="checkout-card checkout-policy">
      <ShieldCheckIcon />
      <div>
        <h2>Cancellation</h2>
        <p>{isCommunityGame ? getCommunityCancellationText(game) : OFFICIAL_CANCELLATION_TEXT}</p>
        {isCommunityGame && <p>{COMMUNITY_PAYMENT_RESPONSIBILITY_TEXT}</p>}
      </div>
    </section>
  )
}
