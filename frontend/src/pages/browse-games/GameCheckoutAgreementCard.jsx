import { useId } from 'react'
import { CheckIcon } from '../../components/BrowseIcons.jsx'
import { LEGAL_POLICY_IDS } from '../../features/legal/legalPolicies.js'

export function GameCheckoutAgreementCard({ agreed, onOpenPolicy, onSetAgreed }) {
  const checkboxId = useId()
  const agreementTextId = useId()

  return (
    <div className="checkout-card checkout-agree">
      <label className="checkout-agree__control" htmlFor={checkboxId}>
        <input
          aria-describedby={agreementTextId}
          aria-label="Agree to Pickup Lane terms"
          checked={agreed}
          className="checkout-agree__input"
          id={checkboxId}
          type="checkbox"
          onChange={(event) => onSetAgreed(event.target.checked)}
        />
        <span className="checkout-agree__box" aria-hidden="true">
          <CheckIcon />
        </span>
      </label>
      <span id={agreementTextId}>
        I agree to the Pickup Lane{' '}
        <button
          className="checkout-legal-link"
          type="button"
          onClick={() => onOpenPolicy(LEGAL_POLICY_IDS.terms)}
        >
          Terms of Service
        </button>{' '}
        and{' '}
        <button
          className="checkout-legal-link"
          type="button"
          onClick={() => onOpenPolicy(LEGAL_POLICY_IDS.cancellationRefunds)}
        >
          Cancellation Policy
        </button>.
      </span>
    </div>
  )
}
