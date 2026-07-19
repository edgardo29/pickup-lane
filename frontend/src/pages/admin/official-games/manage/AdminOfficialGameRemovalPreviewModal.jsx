import { useEffect, useState } from 'react'
import {
  CheckIcon,
  ClipboardListIcon,
  DollarIcon,
  PlusCircleIcon,
  ShieldCheckIcon,
  UsersIcon,
} from '../../../../components/BrowseIcons.jsx'
import { FormErrorMessage } from '../../../../components/FormErrorMessage.jsx'
import { formatAdminGameMoney } from '../shared/adminOfficialGameForm.js'

const executableOutcomes = new Set([
  'remove_only',
  'release_pending_hold_and_remove_party',
  'refund_cash_and_remove_party',
  'restore_credit_and_remove_party',
  'refund_cash_restore_credit_and_remove_party',
])

const outcomeLabels = {
  refund_cash_and_remove_party: 'Refund cash and remove party',
  refund_cash_restore_credit_and_remove_party: 'Refund cash, restore credit, and remove party',
  release_pending_hold_and_remove_party: 'Release hold and remove party',
  remove_only: 'Remove only',
  restore_credit_and_remove_party: 'Restore credit and remove party',
}

function formatState(value) {
  if (!value) {
    return 'None'
  }

  return value
    .split('_')
    .map((part) => `${part.charAt(0).toUpperCase()}${part.slice(1)}`)
    .join(' ')
}

function PreviewFact({ label, value }) {
  return (
    <div className="admin-removal-preview__fact">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

function PreviewSectionHeading({ children, icon }) {
  return (
    <div className="admin-removal-preview__section-heading">
      <span>{icon}</span>
      <h3>{children}</h3>
    </div>
  )
}

function formatExactDateTime(value) {
  if (!value) {
    return ''
  }

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return ''
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date)
}

function AdminOfficialGameRemovalPreviewModal({
  canExecute,
  error,
  executionError,
  executionResult,
  isExecuting,
  isLoading,
  onClose,
  onExecute,
  preview,
  selectedParticipant,
}) {
  const [reason, setReason] = useState('')

  useEffect(() => {
    const originalOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        onClose()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => {
      document.body.style.overflow = originalOverflow
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [onClose])

  const currency = preview?.currency || 'USD'
  const selectedOutcome = preview?.allowed_outcomes?.[0] || ''
  const canConfirm = Boolean(
    preview?.automatic_outcome_available
    && executableOutcomes.has(selectedOutcome)
    && canExecute,
  )

  function handleSubmit(event) {
    event.preventDefault()
    onExecute({
      outcome: selectedOutcome,
      reason: reason.trim(),
    })
  }

  return (
    <div className="admin-official-modal-backdrop" role="presentation" onClick={onClose}>
      <section
        className="admin-official-confirm-modal admin-removal-preview"
        role="dialog"
        aria-modal="true"
        aria-labelledby="admin-removal-preview-title"
        onClick={(event) => event.stopPropagation()}
      >
        <button
          aria-label="Close removal impact"
          className="admin-official-modal-close"
          disabled={isExecuting}
          type="button"
          onClick={onClose}
        >
          <span aria-hidden="true">X</span>
        </button>

        <div className="admin-removal-preview__header">
          <span className="admin-removal-preview__icon">
            <ClipboardListIcon />
          </span>
          <div>
            <h2 id="admin-removal-preview-title">Removal impact</h2>
            <p>{selectedParticipant.display_name_snapshot}</p>
          </div>
        </div>

        {isLoading && (
          <p className="admin-removal-preview__loading" role="status">
            Loading impact.
          </p>
        )}

        {error && <p className="admin-official-alert">{error}</p>}
        {executionError && !canConfirm && (
          <FormErrorMessage className="admin-removal-preview__error">
            {executionError}
          </FormErrorMessage>
        )}

        {preview && !executionResult && (
          <div className="admin-removal-preview__body">
            {preview.blocking_reasons.length > 0 && (
              <FormErrorMessage className="admin-removal-preview__warning">
                {[
                  'Cannot proceed automatically.',
                  ...preview.blocking_reasons,
                ].join(' ')}
              </FormErrorMessage>
            )}

            <section className="admin-removal-preview__section admin-removal-preview__section--summary">
              <PreviewSectionHeading icon={<ShieldCheckIcon />}>
                Removal summary
              </PreviewSectionHeading>
              <div className="admin-removal-preview__facts">
                <PreviewFact label="Scope" value={formatState(preview.removal_scope)} />
                <PreviewFact label="Outcome" value={formatState(preview.classification)} />
                <PreviewFact label="Booking" value={formatState(preview.booking_status)} />
                <PreviewFact label="Payment" value={formatState(preview.booking_payment_status)} />
              </div>
            </section>

            <section className="admin-removal-preview__section">
              <PreviewSectionHeading icon={<DollarIcon />}>
                Money impact
              </PreviewSectionHeading>
              {preview.removal_scope === 'single_participant' && (
                <p className="admin-removal-preview__waitlist-note">
                  Amounts are for the whole booking. This player has no separate payment allocation.
                </p>
              )}
              <div className="admin-removal-preview__money">
                <PreviewFact
                  label="Booking total"
                  value={formatAdminGameMoney(preview.booking_total_cents, currency)}
                />
                <PreviewFact
                  label="Cash collected"
                  value={formatAdminGameMoney(preview.cash_collected_cents, currency)}
                />
                <PreviewFact
                  label="Cash refundable"
                  value={formatAdminGameMoney(preview.cash_refundable_cents, currency)}
                />
                <PreviewFact
                  label="Cash refunded"
                  value={formatAdminGameMoney(preview.cash_refunded_cents, currency)}
                />
                <PreviewFact
                  label="Refund in progress"
                  value={formatAdminGameMoney(preview.cash_refund_pending_cents, currency)}
                />
                <PreviewFact
                  label="Credit restorable"
                  value={formatAdminGameMoney(preview.credit_restorable_cents, currency)}
                />
              </div>
            </section>

            <section className="admin-removal-preview__section">
              <PreviewSectionHeading icon={<UsersIcon />}>
                Affected roster
              </PreviewSectionHeading>
              <div className="admin-removal-preview__participants">
                {preview.affected_participants.map((participant) => (
                  <div key={participant.id}>
                    <span>
                      <strong>{participant.display_name}</strong>
                      {participant.id === selectedParticipant.id
                        && formatExactDateTime(selectedParticipant.joined_at) && (
                          <small>
                            Added {formatExactDateTime(selectedParticipant.joined_at)}
                          </small>
                        )}
                    </span>
                    <em>{formatAdminGameMoney(participant.price_cents, currency)}</em>
                  </div>
                ))}
              </div>
            </section>

            <section className="admin-removal-preview__section">
              <PreviewSectionHeading icon={<PlusCircleIcon />}>
                Capacity and waitlist
              </PreviewSectionHeading>
              <div className="admin-removal-preview__money admin-removal-preview__money--capacity">
                <PreviewFact label="Spots opened" value={preview.spots_opened} />
                <PreviewFact
                  label="Spots available after"
                  value={preview.available_spots_after_removal}
                />
                <PreviewFact
                  label="Waiting parties"
                  value={preview.active_waitlist_entry_count}
                />
                <PreviewFact
                  label="Waiting players"
                  value={preview.active_waitlist_player_count}
                />
              </div>
              <p className="admin-removal-preview__waitlist-note">
                {preview.waitlist_promotion_possible
                  ? 'The next waiting party fits in the available spots.'
                  : 'No waiting party is currently eligible for the opened spots.'}
              </p>
            </section>

            {preview.allowed_outcomes.length > 0 && (
              <section className="admin-removal-preview__section">
                <PreviewSectionHeading icon={<CheckIcon />}>
                  Removal outcome
                </PreviewSectionHeading>
                <p className="admin-removal-preview__outcome">
                  {preview.allowed_outcomes
                    .map((outcome) => outcomeLabels[outcome] || formatState(outcome))
                    .join(', ')}
                </p>
              </section>
            )}

            {preview.automatic_outcome_available
              && executableOutcomes.has(selectedOutcome)
              && (
                <form
                  className="admin-removal-preview__confirm"
                  onSubmit={handleSubmit}
                >
                  <label className="admin-official-textarea-field">
                    <span>Removal reason</span>
                    <textarea
                      maxLength={1000}
                      placeholder="Required internal reason"
                      value={reason}
                      onChange={(event) => setReason(event.target.value)}
                    />
                    <small>{reason.length}/1000</small>
                  </label>

                  <FormErrorMessage className="admin-removal-preview__error">
                    {executionError}
                  </FormErrorMessage>

                  {canExecute && (
                    <div className="admin-official-confirm-modal__actions">
                      <button
                        className="admin-official-button"
                        disabled={isExecuting}
                        type="button"
                        onClick={onClose}
                      >
                        Back
                      </button>
                      <button
                        className="admin-official-button admin-official-button--danger-solid"
                        disabled={isExecuting || !reason.trim() || !canConfirm}
                        type="submit"
                      >
                        {isExecuting ? 'Removing' : 'Confirm removal'}
                      </button>
                    </div>
                  )}
                </form>
              )}
          </div>
        )}

        {executionResult && (
          <div className="admin-removal-preview__result">
            <strong>
              {executionResult.refund_follow_up_required
                ? 'Player removed, follow-up required'
                : 'Player removal completed'}
            </strong>
            <div className="admin-removal-preview__money">
              <PreviewFact
                label="Players removed"
                value={executionResult.removed_participant_ids.length}
              />
              <PreviewFact
                label="Refunds"
                value={executionResult.refunds.length}
              />
              <PreviewFact
                label="Credit restored"
                value={formatAdminGameMoney(
                  executionResult.credit_restored_cents,
                  currency,
                )}
              />
              <PreviewFact
                label="Waitlist advanced"
                value={executionResult.waitlist_advanced_entry_ids.length}
              />
            </div>

            {executionResult.refunds.length > 0 && (
              <div className="admin-removal-preview__participants">
                {executionResult.refunds.map((refund) => (
                  <div key={refund.id}>
                    <span>
                      <strong>{formatState(refund.refund_status)}</strong>
                      <small>Stripe refund</small>
                    </span>
                    <em>{formatAdminGameMoney(refund.amount_cents, refund.currency)}</em>
                  </div>
                ))}
              </div>
            )}

            {executionResult.refund_follow_up_required && (
              <FormErrorMessage className="admin-removal-preview__warning">
                Money support follow-up created. The booking was removed, but at
                least one refund did not finish. The payment remains in its
                truthful state.
              </FormErrorMessage>
            )}
          </div>
        )}

      </section>
    </div>
  )
}

export default AdminOfficialGameRemovalPreviewModal
