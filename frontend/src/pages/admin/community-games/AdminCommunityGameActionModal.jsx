import { useEffect, useMemo, useState } from 'react'
import {
  Ban,
  CircleDollarSign,
  Eye,
  EyeOff,
  PauseCircle,
  PlayCircle,
  RotateCcw,
  X,
} from 'lucide-react'
import { FormErrorMessage } from '../../../components/FormErrorMessage.jsx'
import {
  cancelAdminCommunityGame,
  createAdminMoneyFinancialOutcome,
  hideAdminCommunityGame,
  pauseAdminCommunityGameJoining,
  restoreAdminCommunityGame,
  restoreAdminCommunityGamePaymentText,
  resumeAdminCommunityGameJoining,
} from '../shared/adminApi.js'

const REASON_MAX_LENGTH = 100

const ACTION_CONFIG = {
  hide: {
    api: hideAdminCommunityGame,
    icon: EyeOff,
    keyPrefix: 'admin-community-hide',
    submitLabel: 'Hide game',
    submittingLabel: 'Hiding',
    title: 'Hide community game',
    tone: 'danger',
    summary: 'Hides this game from player-facing community game views.',
  },
  restore: {
    api: restoreAdminCommunityGame,
    icon: Eye,
    keyPrefix: 'admin-community-restore',
    submitLabel: 'Restore game',
    submittingLabel: 'Restoring',
    title: 'Restore community game',
    tone: 'primary',
    summary: 'Returns this hidden game to normal player-facing views.',
  },
  pauseJoining: {
    api: pauseAdminCommunityGameJoining,
    icon: PauseCircle,
    keyPrefix: 'admin-community-pause-joining',
    submitLabel: 'Pause joining',
    submittingLabel: 'Pausing',
    title: 'Pause joining',
    tone: 'danger',
    summary: 'Stops new joins and guest changes while keeping the game visible.',
  },
  resumeJoining: {
    api: resumeAdminCommunityGameJoining,
    icon: PlayCircle,
    keyPrefix: 'admin-community-resume-joining',
    submitLabel: 'Resume joining',
    submittingLabel: 'Resuming',
    title: 'Resume joining',
    tone: 'primary',
    summary: 'Allows eligible players to join and update guests again.',
  },
  cancel: {
    api: cancelAdminCommunityGame,
    icon: Ban,
    keyPrefix: 'admin-community-cancel',
    submitLabel: 'Cancel game',
    submittingLabel: 'Cancelling',
    title: 'Cancel community game',
    tone: 'danger',
    summary: 'Cancels the public game. This action is terminal.',
  },
  restorePaymentText: {
    api: restoreAdminCommunityGamePaymentText,
    icon: RotateCcw,
    keyPrefix: 'admin-community-restore-payment-text',
    resultType: 'paymentText',
    submitLabel: 'Restore payment info',
    submittingLabel: 'Restoring',
    title: 'Restore payment info',
    tone: 'primary',
    summary: 'Shows this host payment info on player-facing game details again.',
  },
}

const PAID_FEE_OUTCOMES = [
  {
    label: 'Manual review',
    value: 'manual_review',
  },
  {
    label: 'Refund publish fee',
    value: 'refund',
  },
  {
    label: 'Credit future publish',
    value: 'credit',
  },
  {
    label: 'Forfeit fee',
    value: 'forfeit',
  },
]

const UNPAID_FEE_OUTCOMES = [
  {
    label: 'No fee charged',
    value: 'no_fee_charged',
  },
  {
    label: 'Manual review',
    value: 'manual_review',
  },
]

function createActionIdempotencyKey(prefix, targetId) {
  const suffix = globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random()}`
  return `${prefix}:${targetId}:${suffix}`
}

function isPaidPublishFee(publishFee) {
  return Boolean(publishFee && publishFee.fee_status === 'paid' && publishFee.amount_cents > 0)
}

function getFinancialOutcomeOptions(publishFee) {
  return isPaidPublishFee(publishFee) ? PAID_FEE_OUTCOMES : UNPAID_FEE_OUTCOMES
}

function getDefaultFinancialOutcome(publishFee) {
  return isPaidPublishFee(publishFee) ? 'manual_review' : 'no_fee_charged'
}

function buildFinancialOutcomePayload({
  detail,
  financialOutcome,
  financialOutcomeIdempotencyKey,
  reason,
}) {
  const payload = {
    outcome: financialOutcome,
    reason,
    internal_note: `Community game cancellation: ${detail.game.id}`,
    idempotency_key: financialOutcomeIdempotencyKey,
    target_game_id: detail.game.id,
  }

  if (detail.publish_fee?.id) {
    payload.host_publish_fee_id = detail.publish_fee.id
  } else {
    payload.host_user_id = detail.host?.id
    payload.amount_cents = 0
  }

  return payload
}

function AdminCommunityGameActionModal({
  action,
  canRecordFinancialOutcome = false,
  detail,
  firebaseUser,
  onClose,
  onCompleted,
}) {
  const config = ACTION_CONFIG[action]
  const [reason, setReason] = useState('')
  const [financialOutcome, setFinancialOutcome] = useState(
    () => getDefaultFinancialOutcome(detail.publish_fee),
  )
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [executionError, setExecutionError] = useState('')
  const [idempotencyKey, setIdempotencyKey] = useState(
    () => createActionIdempotencyKey(config.keyPrefix, detail.game.id),
  )
  const [financialOutcomeIdempotencyKey, setFinancialOutcomeIdempotencyKey] = useState(
    () => createActionIdempotencyKey('admin-community-financial-outcome', detail.game.id),
  )
  const Icon = config.icon
  const showFinancialOutcome = action === 'cancel'
  const canBuildFinancialOutcome = Boolean(detail.publish_fee?.id || detail.host?.id)
  const shouldRecordFinancialOutcome = (
    showFinancialOutcome &&
    canRecordFinancialOutcome &&
    canBuildFinancialOutcome
  )
  const financialOutcomeOptions = useMemo(
    () => getFinancialOutcomeOptions(detail.publish_fee),
    [detail.publish_fee],
  )

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
    if (
      !reason.trim() ||
      isSubmitting ||
      (showFinancialOutcome && canRecordFinancialOutcome && !canBuildFinancialOutcome)
    ) {
      return
    }

    const normalizedReason = reason.trim()
    setIsSubmitting(true)
    setExecutionError('')

    try {
      const actionResult = await config.api({
        firebaseUser,
        gameId: detail.game.id,
        idempotencyKey,
        reason: normalizedReason,
      })

      if (shouldRecordFinancialOutcome) {
        try {
          await createAdminMoneyFinancialOutcome({
            firebaseUser,
            payload: buildFinancialOutcomePayload({
              detail,
              financialOutcome,
              financialOutcomeIdempotencyKey,
              reason: normalizedReason,
            }),
          })
        } catch (error) {
          onCompleted(actionResult, { keepOpen: true })
          throw new Error(
            error.message
              ? `Game action saved, but the publish-fee outcome failed: ${error.message}`
              : 'Game action saved, but the publish-fee outcome failed.',
            { cause: error },
          )
        }
      }

      onCompleted(actionResult)
      onClose()
    } catch (error) {
      setExecutionError(error.message || 'Community game action could not be completed.')
    } finally {
      setIsSubmitting(false)
    }
  }

  function resetActionKeys(nextReason = reason) {
    setIdempotencyKey(createActionIdempotencyKey(config.keyPrefix, detail.game.id))
    setFinancialOutcomeIdempotencyKey(
      createActionIdempotencyKey('admin-community-financial-outcome', detail.game.id),
    )
    setExecutionError('')
    setReason(nextReason)
  }

  function handleReasonChange(event) {
    resetActionKeys(event.target.value)
  }

  function handleFinancialOutcomeChange(event) {
    setFinancialOutcome(event.target.value)
    setFinancialOutcomeIdempotencyKey(
      createActionIdempotencyKey('admin-community-financial-outcome', detail.game.id),
    )
  }

  function handleBackdropClick() {
    if (!isSubmitting) {
      onClose()
    }
  }

  const submitButtonClass = (
    config.tone === 'danger'
      ? 'admin-community-modal__danger'
      : 'admin-community-modal__primary'
  )

  return (
    <div
      className="admin-community-modal-backdrop"
      role="presentation"
      onClick={handleBackdropClick}
    >
      <section
        aria-labelledby="admin-community-action-title"
        aria-modal="true"
        className="admin-community-modal"
        role="dialog"
        onClick={(event) => event.stopPropagation()}
      >
        <header className={`admin-community-modal__header admin-community-modal__header--${config.tone}`}>
          <div>
            <span className="admin-community-modal__icon"><Icon /></span>
            <div>
              <h2 id="admin-community-action-title">{config.title}</h2>
            </div>
          </div>
          <button
            aria-label={`Close ${config.title}`}
            className="admin-community-modal__close"
            disabled={isSubmitting}
            type="button"
            onClick={onClose}
          >
            <X />
          </button>
        </header>

        <form className="admin-community-modal__form" onSubmit={handleSubmit}>
          <p>{config.summary}</p>
          {showFinancialOutcome && (
            <div className="admin-community-modal__money">
              <div>
                <CircleDollarSign />
                <strong>Publish-fee outcome</strong>
              </div>
              {canRecordFinancialOutcome ? (
                <label>
                  <span>Outcome</span>
                  <select
                    disabled={isSubmitting || !canBuildFinancialOutcome}
                    value={financialOutcome}
                    onChange={handleFinancialOutcomeChange}
                  >
                    {financialOutcomeOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
              ) : (
                <p>Admin access is required to record the publish-fee outcome here.</p>
              )}
              {canRecordFinancialOutcome && !canBuildFinancialOutcome && (
                <p>Host context is missing, so the publish-fee outcome cannot be recorded.</p>
              )}
            </div>
          )}

          <label>
            <span>Internal reason</span>
            <textarea
              disabled={isSubmitting}
              maxLength={REASON_MAX_LENGTH}
              placeholder="Required admin reason"
              value={reason}
              onChange={handleReasonChange}
            />
            <small>{reason.length}/{REASON_MAX_LENGTH}</small>
          </label>
          {executionError && (
            <div className="admin-community-modal__message">
              <FormErrorMessage>{executionError}</FormErrorMessage>
            </div>
          )}
          <div className="admin-community-modal__actions">
            <button
              className={submitButtonClass}
              disabled={
                isSubmitting ||
                !reason.trim() ||
                (showFinancialOutcome && canRecordFinancialOutcome && !canBuildFinancialOutcome)
              }
              type="submit"
            >
              <Icon aria-hidden="true" />
              {isSubmitting ? config.submittingLabel : config.submitLabel}
            </button>
          </div>
        </form>
      </section>
    </div>
  )
}

export default AdminCommunityGameActionModal
