import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  ArrowLeft,
  Hash,
  RefreshCw,
  RotateCcw,
} from 'lucide-react'
import { useAuth } from '../../../hooks/useAuth.js'
import '../../../styles/admin/AdminMoneySupport.css'
import {
  AuditSection,
  ContextSection,
  CreditsSection,
  EmptyState,
  PaymentSummary,
  RefundSummary,
  SectionHeader,
  SupportFlagsSection,
} from './AdminMoneyDetailSections.jsx'
import {
  formatMoney,
  formatStatus,
} from './adminMoneyFormatters.js'
import AdminWorkspaceLayout from '../shared/AdminWorkspaceLayout.jsx'
import {
  getAdminMoneyRefund,
  retryAdminMoneyRefund,
} from '../shared/adminApi.js'

const RETRYABLE_REFUND_STATUSES = new Set(['failed', 'cancelled'])
const RETRYABLE_PAYMENT_STATUSES = new Set(['succeeded', 'partially_refunded'])

function buildRefundRetryIdempotencyKey(refundId) {
  const randomValue = globalThis.crypto?.randomUUID?.()
    || `${Date.now()}-${Math.random().toString(36).slice(2)}`

  return `admin-money-refund-retry:${refundId}:${randomValue}`
}

function getRefundRetryEligibility(detail) {
  if (!detail?.refund || !RETRYABLE_REFUND_STATUSES.has(detail.refund.refund_status)) {
    return {
      canRetry: false,
      shouldShow: false,
      message: '',
    }
  }

  if (!detail.payment) {
    return {
      canRetry: false,
      shouldShow: true,
      message: 'Payment context is required before retrying this refund.',
    }
  }

  if (!RETRYABLE_PAYMENT_STATUSES.has(detail.payment.payment_status)) {
    return {
      canRetry: false,
      shouldShow: true,
      message: 'The payment is not in a retryable paid state.',
    }
  }

  if (!detail.payment.paid_at) {
    return {
      canRetry: false,
      shouldShow: true,
      message: 'The payment needs a paid timestamp before retrying this refund.',
    }
  }

  if (!detail.payment.provider_charge_id) {
    return {
      canRetry: false,
      shouldShow: true,
      message: 'A Stripe charge id is required before retrying this refund.',
    }
  }

  return {
    canRetry: true,
    shouldShow: true,
    message: '',
  }
}

function AdminMoneyRefundPage() {
  const { refundId } = useParams()
  const { currentUser } = useAuth()
  const [detail, setDetail] = useState(null)
  const [loadState, setLoadState] = useState('loading')
  const [pageError, setPageError] = useState('')
  const [refreshCount, setRefreshCount] = useState(0)
  const [retryForm, setRetryForm] = useState({ reason: '', refundId: '' })
  const [retryStatus, setRetryStatus] = useState({
    error: '',
    message: '',
    refundId: '',
    state: 'idle',
  })

  useEffect(() => {
    let isMounted = true

    async function loadRefund() {
      if (!currentUser || !refundId) {
        return
      }

      setLoadState('loading')
      setPageError('')

      try {
        const nextDetail = await getAdminMoneyRefund({
          firebaseUser: currentUser,
          refundId,
        })

        if (!isMounted) {
          return
        }

        setDetail(nextDetail)
        setLoadState('ready')
      } catch (error) {
        if (!isMounted) {
          return
        }

        setDetail(null)
        setPageError(error.message || 'Refund detail could not be loaded.')
        setLoadState('error')
      }
    }

    loadRefund()

    return () => {
      isMounted = false
    }
  }, [currentUser, refundId, refreshCount])

  const pageTitle = useMemo(() => (
    detail?.refund
      ? `${formatMoney(detail.refund.amount_cents, detail.refund.currency)} ${formatStatus(detail.refund.refund_status)}`
      : 'Refund Detail'
  ), [detail])
  const retryEligibility = useMemo(() => getRefundRetryEligibility(detail), [detail])
  const retryReason = retryForm.refundId === refundId ? retryForm.reason : ''
  const activeRetryStatus = retryStatus.refundId === refundId
    ? retryStatus
    : {
      error: '',
      message: '',
      state: 'idle',
    }
  const backPath = detail?.payment?.id
    ? `/admin/money/payments/${detail.payment.id}`
    : '/admin/money/refunds'
  const backLabel = detail?.payment?.id ? 'Payment detail' : 'Refunds'
  const retrySubmitting = activeRetryStatus.state === 'submitting'

  async function handleRefundRetry(event) {
    event.preventDefault()

    const reason = retryReason.trim()
    if (!retryEligibility.canRetry) {
      setRetryStatus({
        error: retryEligibility.message || 'This refund cannot be retried.',
        message: '',
        refundId,
        state: 'idle',
      })
      return
    }
    if (reason.length < 3) {
      setRetryStatus({
        error: 'Reason is required.',
        message: '',
        refundId,
        state: 'idle',
      })
      return
    }

    setRetryStatus({
      error: '',
      message: '',
      refundId,
      state: 'submitting',
    })

    try {
      const nextDetail = await retryAdminMoneyRefund({
        firebaseUser: currentUser,
        refundId,
        reason,
        idempotencyKey: buildRefundRetryIdempotencyKey(refundId),
      })

      setDetail(nextDetail)
      setRetryForm({ reason: '', refundId })
      setRetryStatus({
        error: '',
        message: `Retry recorded as ${formatStatus(nextDetail.refund.refund_status)}.`,
        refundId,
        state: 'idle',
      })
    } catch (error) {
      setRetryStatus({
        error: error.message || 'Refund retry could not be completed.',
        message: '',
        refundId,
        state: 'idle',
      })
    }
  }

  return (
    <>
      <AdminWorkspaceLayout
        breadcrumbs={['Admin', 'Money', 'Refunds']}
        description="Inspect this refund, its payment context, and retry or support state."
        icon={RotateCcw}
        title={pageTitle}
      >
        <div className="admin-money-layout">
          <div className="admin-money-toolbar">
            <Link className="admin-money-button" to={backPath}>
              <ArrowLeft />
              {backLabel}
            </Link>
            <button
              className="admin-money-button"
              type="button"
              onClick={() => setRefreshCount((count) => count + 1)}
            >
              <RefreshCw />
              Refresh
            </button>
          </div>

          {pageError && (
            <div className="admin-money-alert" role="alert">
              {pageError}
            </div>
          )}

          {loadState === 'loading' && (
            <section className="admin-money-panel">
              <EmptyState>Loading refund detail.</EmptyState>
            </section>
          )}

          {loadState === 'ready' && detail && (
            <>
              <RefundSummary refund={detail.refund} />
              {retryEligibility.shouldShow && (
                <section className="admin-money-panel" aria-label="Refund retry">
                  <SectionHeader icon={RotateCcw} title="Retry Refund" />
                  <form className="admin-money-action-form" onSubmit={handleRefundRetry}>
                    <label>
                      <span>Reason</span>
                      <textarea
                        disabled={!retryEligibility.canRetry || retrySubmitting}
                        maxLength={1000}
                        onChange={(event) => {
                          setRetryForm({
                            reason: event.target.value,
                            refundId,
                          })
                        }}
                        rows={3}
                        value={retryReason}
                      />
                    </label>
                    <div className="admin-money-action-bar">
                      <div className="admin-money-action-status">
                        {!retryEligibility.canRetry && retryEligibility.message && (
                          <p className="admin-money-form-error" role="status">
                            {retryEligibility.message}
                          </p>
                        )}
                        {activeRetryStatus.error && (
                          <p className="admin-money-form-error" role="alert">
                            {activeRetryStatus.error}
                          </p>
                        )}
                        {activeRetryStatus.message && (
                          <p className="admin-money-form-success" role="status">
                            {activeRetryStatus.message}
                          </p>
                        )}
                      </div>
                      <button
                        className="admin-money-button admin-money-button--primary"
                        disabled={!retryEligibility.canRetry || retrySubmitting}
                        type="submit"
                      >
                        <RotateCcw />
                        {retrySubmitting ? 'Retrying' : 'Retry Stripe Refund'}
                      </button>
                    </div>
                  </form>
                </section>
              )}
              {detail.payment ? (
                <PaymentSummary payment={detail.payment} />
              ) : (
                <section className="admin-money-panel" aria-label="Payment summary">
                  <EmptyState>No payment context.</EmptyState>
                </section>
              )}
              <ContextSection booking={detail.booking} game={detail.game} />
              <CreditsSection
                creditGrants={detail.credit_grants ?? []}
                creditUsages={detail.credit_usages ?? []}
              />
              <SupportFlagsSection supportFlags={detail.support_flags ?? []} />
              <AuditSection auditActions={detail.audit_actions ?? []} />
              <section className="admin-money-panel" aria-label="Support boundary">
                <SectionHeader icon={Hash} title="Support Boundary" />
                <p className="admin-money-note">
                  Refund state changes only after the backend records Stripe's result.
                  Support flags remain separate until staff resolves the follow-up item.
                </p>
              </section>
            </>
          )}
        </div>
      </AdminWorkspaceLayout>
    </>
  )
}

export default AdminMoneyRefundPage
