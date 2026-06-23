import { useEffect, useState } from 'react'
import { RotateCcw, Send } from 'lucide-react'
import { FormErrorMessage } from '../../../components/FormErrorMessage.jsx'
import {
  retryFailedPlatformNoticeCampaign,
  sendPlatformNoticeCampaign,
} from '../shared/adminApi.js'
import {
  createPlatformNoticeDeliveryIdempotencyKey,
  formatPlatformNoticeLabel,
} from './adminPlatformNoticeData.js'

function AdminPlatformNoticeDeliveryModal({
  campaign,
  currentUser,
  onClose,
  onComplete,
  operation,
}) {
  const [confirmed, setConfirmed] = useState(false)
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [idempotencyKey] = useState(() => (
    createPlatformNoticeDeliveryIdempotencyKey(campaign.id, operation)
  ))
  const isRetry = operation === 'retry'
  const recipientCount = isRetry
    ? campaign.delivery_summary?.failed_count || 0
    : campaign.audience_type === 'selected_users'
      ? campaign.target_user_count || 0
      : 'All active'

  useEffect(() => {
    const originalOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    function handleKeyDown(event) {
      if (event.key === 'Escape' && !isSubmitting) {
        onClose()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => {
      document.body.style.overflow = originalOverflow
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [isSubmitting, onClose])

  async function handleSubmit(event) {
    event.preventDefault()
    if (!confirmed || isSubmitting) {
      return
    }

    setIsSubmitting(true)
    setError('')
    try {
      const result = isRetry
        ? await retryFailedPlatformNoticeCampaign({
          campaignId: campaign.id,
          firebaseUser: currentUser,
          idempotencyKey,
        })
        : await sendPlatformNoticeCampaign({
          campaignId: campaign.id,
          firebaseUser: currentUser,
          idempotencyKey,
        })
      onComplete(result)
      onClose()
    } catch (requestError) {
      setError(
        requestError.message
        || (isRetry ? 'Failed deliveries could not be retried.' : 'Campaign could not be sent.'),
      )
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div
      className="admin-platform-notices-modal-backdrop"
      role="presentation"
      onClick={() => {
        if (!isSubmitting) {
          onClose()
        }
      }}
    >
      <section
        aria-labelledby="admin-platform-notices-delivery-title"
        aria-modal="true"
        className="admin-platform-notices-modal"
        role="dialog"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="admin-platform-notices-modal__header">
          <span>{isRetry ? <RotateCcw /> : <Send />}</span>
          <div>
            <h2 id="admin-platform-notices-delivery-title">
              {isRetry ? 'Retry failed deliveries?' : 'Send campaign?'}
            </h2>
            <p>{campaign.internal_name}</p>
          </div>
        </header>

        <form className="admin-platform-notices-modal__form" onSubmit={handleSubmit}>
          <div className="admin-platform-notices-modal__facts">
            <div>
              <span>Recipients</span>
              <strong>{recipientCount}</strong>
            </div>
            <div>
              <span>Audience</span>
              <strong>{formatPlatformNoticeLabel(campaign.audience_type)}</strong>
            </div>
            <div>
              <span>Title</span>
              <strong>{campaign.title}</strong>
            </div>
          </div>

          <label className="admin-platform-notices-modal__confirm">
            <input
              checked={confirmed}
              disabled={isSubmitting}
              type="checkbox"
              onChange={(event) => setConfirmed(event.target.checked)}
            />
            <span>
              {isRetry
                ? 'Retry only the currently failed recipients.'
                : 'Confirm this audience and notice copy.'}
            </span>
          </label>

          <FormErrorMessage>{error}</FormErrorMessage>

          <div className="admin-platform-notices-modal__actions">
            <button
              className="admin-platform-notices-modal__secondary"
              disabled={isSubmitting}
              type="button"
              onClick={onClose}
            >
              Back
            </button>
            <button
              className="admin-platform-notices-modal__primary"
              disabled={!confirmed || isSubmitting}
              type="submit"
            >
              {isSubmitting
                ? (isRetry ? 'Retrying' : 'Sending')
                : (isRetry ? 'Retry failed' : 'Send campaign')}
            </button>
          </div>
        </form>
      </section>
    </div>
  )
}

export default AdminPlatformNoticeDeliveryModal
