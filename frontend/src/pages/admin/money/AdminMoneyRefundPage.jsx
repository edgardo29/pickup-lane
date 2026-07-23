import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  ArrowLeft,
  Hash,
  RefreshCw,
  RotateCcw,
  Search,
} from 'lucide-react'
import { useAuth } from '../../../hooks/useAuth.js'
import '../../../styles/admin/AdminMoneySupport.css'
import {
  AuditSection,
  ContextSection,
  CreditsSection,
  EmptyState,
  MoneyIssuesSection,
  PaymentSummary,
  RefundEventsSection,
  RefundSummary,
  SectionHeader,
} from './AdminMoneyDetailSections.jsx'
import {
  formatMoney,
  formatStatus,
} from './adminMoneyFormatters.js'
import AdminWorkspaceLayout from '../shared/AdminWorkspaceLayout.jsx'
import {
  getAdminMoneyRefund,
  reconcileAdminMoneyRefund,
  retryAdminMoneyRefund,
} from '../shared/adminApi.js'

function buildRefundRetryIdempotencyKey(refundId) {
  const randomValue = globalThis.crypto?.randomUUID?.()
    || `${Date.now()}-${Math.random().toString(36).slice(2)}`

  return `admin-money-refund-retry:${refundId}:${randomValue}`
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
  const [reconcileForm, setReconcileForm] = useState({ reason: '', refundId: '' })
  const [reconcileStatus, setReconcileStatus] = useState({
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
  const availableActions = useMemo(() => {
    const actions = new Map()
    for (const action of detail?.available_actions ?? []) {
      if (action?.action_code) {
        actions.set(action.action_code, action)
      }
    }
    return actions
  }, [detail])
  const paymentSummary = detail?.payment_summary ?? null
  const bookingSummary = detail?.booking_summary ?? null
  const gameSummary = detail?.game_summary ?? null
  const userSummary = detail?.user_summary ?? null
  const participantSummary = detail?.participant_summary ?? null
  const publishFeeSummary = detail?.publish_fee_summary ?? null
  const creditContext = detail?.credit_context ?? {}
  const creditGrants = creditContext.credit_grants ?? []
  const creditUsages = creditContext.credit_usages ?? []
  const recentRefundEvents = detail?.recent_refund_events ?? []
  const adminActivity = detail?.admin_activity ?? []
  const canRetryRefund = Boolean(availableActions.get('retry_refund')?.enabled)
  const canCheckStripeStatus = Boolean(
    availableActions.get('check_provider_status')?.enabled,
  )
  const retryReason = retryForm.refundId === refundId ? retryForm.reason : ''
  const activeRetryStatus = retryStatus.refundId === refundId
    ? retryStatus
    : {
      error: '',
      message: '',
      state: 'idle',
    }
  const backPath = paymentSummary?.id
    ? `/admin/money/payments/${paymentSummary.id}`
    : '/admin/money/refunds'
  const backLabel = paymentSummary?.id ? 'Payment detail' : 'Refunds'
  const retrySubmitting = activeRetryStatus.state === 'submitting'
  const activeReconcileStatus = reconcileStatus.refundId === refundId
    ? reconcileStatus
    : {
      error: '',
      message: '',
      state: 'idle',
    }
  const reconcileReason = reconcileForm.refundId === refundId ? reconcileForm.reason : ''
  const reconcileSubmitting = activeReconcileStatus.state === 'submitting'

  async function handleRefundRetry(event) {
    event.preventDefault()

    const reason = retryReason.trim()
    if (!canRetryRefund) {
      setRetryStatus({
        error: 'This refund cannot be retried.',
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

  async function handleRefundReconcile(event) {
    event.preventDefault()

    const reason = reconcileReason.trim()
    if (reason.length < 3) {
      setReconcileStatus({
        error: 'Reason is required.',
        message: '',
        refundId,
        state: 'idle',
      })
      return
    }

    setReconcileStatus({
      error: '',
      message: '',
      refundId,
      state: 'submitting',
    })

    try {
      const nextDetail = await reconcileAdminMoneyRefund({
        firebaseUser: currentUser,
        refundId,
        reason,
        idempotencyKey: buildRefundRetryIdempotencyKey(`reconcile:${refundId}`),
      })

      setDetail(nextDetail)
      setReconcileForm({ reason: '', refundId })
      setReconcileStatus({
        error: '',
        message: 'Stripe status checked.',
        refundId,
        state: 'idle',
      })
    } catch (error) {
      setReconcileStatus({
        error: error.message || 'Reconciliation check could not be recorded.',
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
        description="Inspect this refund, its payment context, provider events, and linked money issue."
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
              <RefundSummary
                providerSnapshot={detail.current_provider_snapshot}
                refund={detail.refund}
              />
              {canRetryRefund && (
                <section className="admin-money-panel" aria-label="Refund retry">
                  <SectionHeader icon={RotateCcw} title="Retry Refund" />
                  <form className="admin-money-action-form" onSubmit={handleRefundRetry}>
                    <label>
                      <span>Reason</span>
                      <textarea
                        disabled={!canRetryRefund || retrySubmitting}
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
                        disabled={!canRetryRefund || retrySubmitting}
                        type="submit"
                      >
                        <RotateCcw />
                        {retrySubmitting ? 'Retrying' : 'Retry Stripe Refund'}
                      </button>
                    </div>
                  </form>
                </section>
              )}
              {canCheckStripeStatus && (
                <section className="admin-money-panel" aria-label="Refund reconciliation">
                  <SectionHeader icon={Search} title="Check Stripe Status" />
                  <form className="admin-money-action-form" onSubmit={handleRefundReconcile}>
                    <label>
                      <span>Reason</span>
                      <textarea
                        disabled={reconcileSubmitting}
                        maxLength={1000}
                        onChange={(event) => {
                          setReconcileForm({
                            reason: event.target.value,
                            refundId,
                          })
                        }}
                        rows={3}
                        value={reconcileReason}
                      />
                    </label>
                    <div className="admin-money-action-bar">
                      <div className="admin-money-action-status">
                        {activeReconcileStatus.error && (
                          <p className="admin-money-form-error" role="alert">
                            {activeReconcileStatus.error}
                          </p>
                        )}
                        {activeReconcileStatus.message && (
                          <p className="admin-money-form-success" role="status">
                            {activeReconcileStatus.message}
                          </p>
                        )}
                      </div>
                      <button
                        className="admin-money-button"
                        disabled={reconcileSubmitting}
                        type="submit"
                      >
                        <Search />
                        {reconcileSubmitting ? 'Checking' : 'Check Stripe Status'}
                      </button>
                    </div>
                  </form>
                </section>
              )}
              {paymentSummary ? (
                <PaymentSummary payment={paymentSummary} />
              ) : (
                <section className="admin-money-panel" aria-label="Payment summary">
                  <EmptyState>No payment context.</EmptyState>
                </section>
              )}
              <ContextSection
                booking={bookingSummary}
                game={gameSummary}
                hostPublishFee={publishFeeSummary}
                participant={participantSummary}
                userSummary={userSummary}
              />
              <CreditsSection
                creditGrants={creditGrants}
                creditUsages={creditUsages}
              />
              <RefundEventsSection refundEvents={recentRefundEvents} />
              <MoneyIssuesSection moneyIssues={detail.linked_money_issue ? [detail.linked_money_issue] : []} />
              {adminActivity.length > 0 && (
                <AuditSection auditActions={adminActivity} />
              )}
              <section className="admin-money-panel" aria-label="Issue boundary">
                <SectionHeader icon={Hash} title="Issue Boundary" />
                <p className="admin-money-note">
                  Refund state changes only after the backend records Stripe's result.
                  Resolving a Money Issue closes staff follow-up only; it does not rewrite refund truth.
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
