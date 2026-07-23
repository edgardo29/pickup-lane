import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  ArrowLeft,
  RefreshCw,
  WalletCards,
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
  RefundsSection,
} from './AdminMoneyDetailSections.jsx'
import {
  formatMoney,
  formatStatus,
} from './adminMoneyFormatters.js'
import AdminWorkspaceLayout from '../shared/AdminWorkspaceLayout.jsx'
import { getAdminMoneyPayment } from '../shared/adminApi.js'

function AdminMoneyPaymentPage() {
  const { paymentId } = useParams()
  const { currentUser } = useAuth()
  const [detail, setDetail] = useState(null)
  const [loadState, setLoadState] = useState('loading')
  const [pageError, setPageError] = useState('')
  const [refreshCount, setRefreshCount] = useState(0)

  useEffect(() => {
    let isMounted = true

    async function loadPayment() {
      if (!currentUser || !paymentId) {
        return
      }

      setLoadState('loading')
      setPageError('')

      try {
        const nextDetail = await getAdminMoneyPayment({
          firebaseUser: currentUser,
          paymentId,
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
        setPageError(error.message || 'Payment detail could not be loaded.')
        setLoadState('error')
      }
    }

    loadPayment()

    return () => {
      isMounted = false
    }
  }, [currentUser, paymentId, refreshCount])

  const pageTitle = useMemo(() => (
    detail?.payment
      ? `${formatMoney(detail.payment.amount_cents, detail.payment.currency)} ${formatStatus(detail.payment.payment_status)}`
      : 'Payment Detail'
  ), [detail])
  const hasOfficialGameContext = detail?.game?.game_type === 'official' && detail.game.id
  const backPath = hasOfficialGameContext
    ? `/admin/official-games/${detail.game.id}`
    : '/admin/money/payments'
  const backLabel = hasOfficialGameContext ? 'Official game' : 'Payments'

  return (
    <>
      <AdminWorkspaceLayout
        breadcrumbs={['Admin', 'Money', 'Payments']}
        description="Inspect this payment and its related booking, refund, credit, and issue context."
        icon={WalletCards}
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
              <EmptyState>Loading payment detail.</EmptyState>
            </section>
          )}

          {loadState === 'ready' && detail && (
            <>
              <PaymentSummary payer={detail.payer} payment={detail.payment} />
              <ContextSection
                booking={detail.booking}
                communityPublishAttempt={detail.community_publish_attempt}
                game={detail.game}
                hostPublishFee={detail.host_publish_fee}
                publishHost={detail.publish_host}
              />
              <RefundsSection refunds={detail.refunds ?? []} />
              <CreditsSection
                creditGrants={detail.credit_grants ?? []}
                creditUsages={detail.credit_usages ?? []}
              />
              <MoneyIssuesSection moneyIssues={detail.linked_money_issues ?? []} />
              {Boolean(detail.admin_actions?.length) && (
                <AuditSection auditActions={detail.admin_actions} />
              )}
            </>
          )}
        </div>
      </AdminWorkspaceLayout>
    </>
  )
}

export default AdminMoneyPaymentPage
