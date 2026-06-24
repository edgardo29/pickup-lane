import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  ArrowLeft,
  CircleDollarSign,
  Hash,
  RefreshCw,
} from 'lucide-react'
import { AppPageShell } from '../../../components/app/index.js'
import { useAuth } from '../../../hooks/useAuth.js'
import '../../../styles/admin/AdminMoneySupport.css'
import {
  AuditSection,
  ContextSection,
  CreditSummary,
  CreditUsagesSection,
  EmptyState,
  PaymentsSection,
  RefundsSection,
  SectionHeader,
  SupportFlagsSection,
} from './AdminMoneyDetailSections.jsx'
import {
  formatMoney,
  formatStatus,
} from './adminMoneyFormatters.js'
import AdminWorkspaceLayout from '../shared/AdminWorkspaceLayout.jsx'
import { getAdminMoneyCredit } from '../shared/adminApi.js'

function AdminMoneyCreditPage() {
  const { creditId } = useParams()
  const { currentUser } = useAuth()
  const [detail, setDetail] = useState(null)
  const [loadState, setLoadState] = useState('loading')
  const [pageError, setPageError] = useState('')
  const [refreshCount, setRefreshCount] = useState(0)

  useEffect(() => {
    let isMounted = true

    async function loadCredit() {
      if (!currentUser || !creditId) {
        return
      }

      setLoadState('loading')
      setPageError('')

      try {
        const nextDetail = await getAdminMoneyCredit({
          creditId,
          firebaseUser: currentUser,
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
        setPageError(error.message || 'Money credit could not be loaded.')
        setLoadState('error')
      }
    }

    loadCredit()

    return () => {
      isMounted = false
    }
  }, [creditId, currentUser, refreshCount])

  const pageTitle = useMemo(() => (
    detail?.credit
      ? `${formatMoney(detail.credit.remaining_cents, detail.credit.currency)} ${formatStatus(detail.credit.credit_status)}`
      : 'Credit Detail'
  ), [detail])

  return (
    <AppPageShell className="admin-page" mainClassName="admin-shell">
      <AdminWorkspaceLayout
        breadcrumbs={['Admin', 'Money', 'Credits']}
        description="Inspect this credit, its usage, and related money support context."
        icon={CircleDollarSign}
        title={pageTitle}
      >
        <div className="admin-money-layout">
          <div className="admin-money-toolbar">
            <Link className="admin-money-button" to="/admin/money/credits">
              <ArrowLeft />
              Credits
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
              <EmptyState>Loading money credit.</EmptyState>
            </section>
          )}

          {loadState === 'ready' && detail && (
            <>
              <CreditSummary credit={detail.credit} />
              <CreditUsagesSection creditUsages={detail.credit_usages ?? []} />
              <PaymentsSection payments={detail.payments ?? []} />
              <RefundsSection refunds={detail.refunds ?? []} />
              <ContextSection booking={detail.booking} game={detail.game} />
              <SupportFlagsSection supportFlags={detail.support_flags ?? []} />
              <AuditSection auditActions={detail.audit_actions ?? []} />
              <section className="admin-money-panel" aria-label="Read-only status">
                <SectionHeader icon={Hash} title="Read Only" />
                <p className="admin-money-note">
                  This page shows backend credit truth only. It does not issue,
                  reverse, restore, release, or resolve support flags.
                </p>
              </section>
            </>
          )}
        </div>
      </AdminWorkspaceLayout>
    </AppPageShell>
  )
}

export default AdminMoneyCreditPage
