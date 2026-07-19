import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  ArrowLeft,
  CircleDollarSign,
  FileClock,
  Hash,
  RefreshCw,
} from 'lucide-react'
import { useAuth } from '../../../hooks/useAuth.js'
import '../../../styles/admin/AdminMoneySupport.css'
import AdminWorkspaceLayout from '../shared/AdminWorkspaceLayout.jsx'
import { getAdminMoneyFinancialOutcome } from '../shared/adminApi.js'
import {
  DetailCodeField,
  DetailField,
  EmptyState,
  SectionHeader,
} from './AdminMoneyDetailSections.jsx'
import {
  formatDateTime,
  formatMoney,
  formatStatus,
} from './adminMoneyFormatters.js'

function RelatedTargets({ outcome }) {
  const links = [
    outcome.target_game_id && {
      href: `/admin/community-games/${outcome.target_game_id}`,
      label: 'Community game',
      value: outcome.target_game_id,
    },
    outcome.payment_id && {
      href: `/admin/money/payments/${outcome.payment_id}`,
      label: 'Payment',
      value: outcome.payment_id,
    },
    outcome.refund_id && {
      href: `/admin/money/refunds/${outcome.refund_id}`,
      label: 'Refund',
      value: outcome.refund_id,
    },
    outcome.host_user_id && {
      href: `/admin/users/${outcome.host_user_id}`,
      label: 'Host user',
      value: outcome.host_user_id,
    },
  ].filter(Boolean)

  return (
    <section className="admin-money-panel" aria-label="Related targets">
      <SectionHeader count={links.length} icon={Hash} title="Related Targets" />
      {links.length === 0 ? (
        <EmptyState>No related target links.</EmptyState>
      ) : (
        <div className="admin-money-row-list">
          {links.map((link) => (
            <div className="admin-money-row" key={link.href}>
              <div>
                <Link className="admin-money-row-link" to={link.href}>
                  {link.label}
                </Link>
                <span>{link.value}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}

function AdminMoneyFinancialOutcomePage() {
  const { financialOutcomeId } = useParams()
  const { currentUser } = useAuth()
  const [outcome, setOutcome] = useState(null)
  const [loadState, setLoadState] = useState('loading')
  const [pageError, setPageError] = useState('')
  const [refreshCount, setRefreshCount] = useState(0)

  useEffect(() => {
    let isMounted = true

    async function loadOutcome() {
      if (!currentUser || !financialOutcomeId) return

      setLoadState('loading')
      setPageError('')

      try {
        const nextOutcome = await getAdminMoneyFinancialOutcome({
          financialOutcomeId,
          firebaseUser: currentUser,
        })
        if (!isMounted) return

        setOutcome(nextOutcome)
        setLoadState('ready')
      } catch (error) {
        if (!isMounted) return

        setOutcome(null)
        setPageError(error.message || 'Financial outcome could not be loaded.')
        setLoadState('error')
      }
    }

    loadOutcome()

    return () => {
      isMounted = false
    }
  }, [currentUser, financialOutcomeId, refreshCount])

  const pageTitle = useMemo(() => (
    outcome
      ? `${formatStatus(outcome.outcome)} · ${formatStatus(outcome.applied_status)}`
      : 'Financial Outcome'
  ), [outcome])

  return (
    <AdminWorkspaceLayout
      breadcrumbs={['Admin', 'Money', 'Financial Outcomes']}
      description="Inspect a publish-fee financial outcome and its linked records."
      icon={CircleDollarSign}
      title={pageTitle}
    >
      <div className="admin-money-layout">
        <div className="admin-money-toolbar">
          <Link className="admin-money-button" to="/admin/review-cases">
            <ArrowLeft />
            Review cases
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
            <EmptyState>Loading financial outcome.</EmptyState>
          </section>
        )}

        {loadState === 'ready' && outcome && (
          <>
            <section className="admin-money-panel" aria-label="Financial outcome">
              <SectionHeader icon={CircleDollarSign} title="Outcome" />
              <div className="admin-money-kpis">
                <div>
                  <span>Outcome</span>
                  <strong>{formatStatus(outcome.outcome)}</strong>
                </div>
                <div>
                  <span>Applied</span>
                  <strong>{formatStatus(outcome.applied_status)}</strong>
                </div>
                <div>
                  <span>Amount</span>
                  <strong>{formatMoney(outcome.amount_cents, outcome.currency)}</strong>
                </div>
                <div>
                  <span>Currency</span>
                  <strong>{outcome.currency}</strong>
                </div>
              </div>
              <div className="admin-money-field-grid">
                <DetailCodeField label="Outcome ID" value={outcome.id} />
                <DetailCodeField label="Host publish fee" value={outcome.host_publish_fee_id} />
                <DetailCodeField label="Entitlement" value={outcome.host_publish_entitlement_id} />
                <DetailCodeField label="Admin action" value={outcome.admin_action_id} />
                <DetailCodeField label="Review case" value={outcome.review_case_id} />
                <DetailField label="Reason" value={outcome.reason} />
                <DetailField label="Internal note" value={outcome.internal_note} />
                <DetailField label="Failure" value={outcome.failure_reason} />
                <DetailField label="Applied at" value={formatDateTime(outcome.applied_at)} />
                <DetailField label="Created" value={formatDateTime(outcome.created_at)} />
                <DetailField label="Updated" value={formatDateTime(outcome.updated_at)} />
              </div>
            </section>

            <RelatedTargets outcome={outcome} />

            <section className="admin-money-panel" aria-label="Read-only status">
              <SectionHeader icon={FileClock} title="Read Only" />
              <p className="admin-money-note">
                This page shows the recorded admin money decision. Outcome changes
                must be made through the supported admin workflows.
              </p>
            </section>
          </>
        )}
      </div>
    </AdminWorkspaceLayout>
  )
}

export default AdminMoneyFinancialOutcomePage
