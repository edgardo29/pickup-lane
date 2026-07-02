import { ShieldCheckIcon } from '../../components/BrowseIcons.jsx'

export function GameCheckoutPolicyCard() {
  return (
    <section className="checkout-card checkout-policy">
      <ShieldCheckIcon />
      <div>
        <h2>Cancellation</h2>
        <p>
          Free cancellation up to 24 hours before game time. After that, refunds are not issued.
        </p>
      </div>
    </section>
  )
}
