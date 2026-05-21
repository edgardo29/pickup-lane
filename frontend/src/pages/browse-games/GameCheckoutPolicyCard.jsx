import { Link } from 'react-router-dom'
import { ShieldCheckIcon } from '../../components/BrowseIcons.jsx'

export function GameCheckoutPolicyCard({ gameId }) {
  return (
    <section className="checkout-card checkout-policy">
      <ShieldCheckIcon />
      <div>
        <h2>Cancellation</h2>
        <p>
          Free cancellation up to 24 hours before game time. After that, refunds are not issued.
        </p>
        <Link
          to="/policies/cancellation-refunds"
          state={{ from: `/games/${gameId}/checkout`, fromLabel: 'Back to checkout' }}
        >
          View policy
        </Link>
      </div>
    </section>
  )
}
