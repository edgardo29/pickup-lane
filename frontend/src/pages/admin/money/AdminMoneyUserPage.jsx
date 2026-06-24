import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  CreditCard,
  RefreshCw,
  Search,
  UserRound,
} from 'lucide-react'
import { AppPageShell } from '../../../components/app/index.js'
import { useAuth } from '../../../hooks/useAuth.js'
import '../../../styles/admin/AdminMoneySupport.css'
import {
  AuditSection,
  CreditsSection,
  DetailCodeField,
  DetailField,
  EmptyState,
  PaymentsSection,
  RefundsSection,
  SectionHeader,
  SupportFlagsSection,
} from './AdminMoneyDetailSections.jsx'
import {
  formatDateTime,
  formatStatus,
  shortId,
} from './adminMoneyFormatters.js'
import AdminWorkspaceLayout from '../shared/AdminWorkspaceLayout.jsx'
import { getAdminMoneyUser } from '../shared/adminApi.js'

function formatUserName(user) {
  return [user?.first_name, user?.last_name].filter(Boolean).join(' ') || user?.email || 'User'
}

function formatExpiry(method) {
  if (!method?.exp_month || !method?.exp_year) {
    return 'No expiry'
  }

  return `${String(method.exp_month).padStart(2, '0')}/${method.exp_year}`
}

function UserSummary({ user }) {
  return (
    <section className="admin-money-panel" aria-label="User summary">
      <SectionHeader icon={UserRound} title="User" />
      <div className="admin-money-kpis">
        <div>
          <span>Name</span>
          <strong>{formatUserName(user)}</strong>
        </div>
        <div>
          <span>Account</span>
          <strong>{formatStatus(user.account_status)}</strong>
        </div>
        <div>
          <span>Role</span>
          <strong>{formatStatus(user.role)}</strong>
        </div>
        <div>
          <span>Hosting</span>
          <strong>{formatStatus(user.hosting_status)}</strong>
        </div>
      </div>
      <div className="admin-money-field-grid">
        <DetailCodeField label="User ID" value={user.id} />
        <DetailField label="Email" value={user.email || 'No email'} />
        <DetailField label="Member since" value={formatDateTime(user.member_since)} />
        <DetailField label="Created" value={formatDateTime(user.created_at)} />
        <DetailField label="Updated" value={formatDateTime(user.updated_at)} />
        <DetailField label="Deleted" value={formatDateTime(user.deleted_at)} />
      </div>
    </section>
  )
}

function PaymentMethodsSection({ paymentMethods }) {
  return (
    <section className="admin-money-panel" aria-label="Saved cards">
      <SectionHeader count={paymentMethods.length} icon={CreditCard} title="Saved Cards" />
      {paymentMethods.length === 0 ? (
        <EmptyState>No saved cards found.</EmptyState>
      ) : (
        <div className="admin-money-row-list">
          {paymentMethods.map((method) => (
            <div className="admin-money-row admin-money-row--four" key={method.id}>
              <div>
                <strong>{formatStatus(method.card_brand)} ending {method.card_last4}</strong>
                <span>{method.is_default ? 'Default' : 'Not default'}</span>
              </div>
              <div>
                <span>{formatExpiry(method)}</span>
                <span>{formatStatus(method.method_status)}</span>
              </div>
              <div>
                <span>Created {formatDateTime(method.created_at)}</span>
                <span>Updated {formatDateTime(method.updated_at)}</span>
              </div>
              <div>
                <span>Detached {formatDateTime(method.detached_at)}</span>
                <span>User {shortId(method.user_id)}</span>
                <code>{shortId(method.id)}</code>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}

function AdminMoneyUserPage() {
  const { userId } = useParams()
  const navigate = useNavigate()
  const { currentUser } = useAuth()
  const [draftUserSearch, setDraftUserSearch] = useState({
    userId: userId || '',
    value: userId || '',
  })
  const [includeInactivePaymentMethods, setIncludeInactivePaymentMethods] = useState(false)
  const [detail, setDetail] = useState(null)
  const [loadState, setLoadState] = useState(userId ? 'loading' : 'idle')
  const [pageError, setPageError] = useState('')
  const [refreshCount, setRefreshCount] = useState(0)

  useEffect(() => {
    let isMounted = true

    async function loadUserMoney() {
      if (!currentUser || !userId) {
        setDetail(null)
        setLoadState('idle')
        return
      }

      setLoadState('loading')
      setPageError('')

      try {
        const nextDetail = await getAdminMoneyUser({
          firebaseUser: currentUser,
          includeInactivePaymentMethods,
          userId,
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
        setPageError(error.message || 'User money summary could not be loaded.')
        setLoadState('error')
      }
    }

    loadUserMoney()

    return () => {
      isMounted = false
    }
  }, [currentUser, includeInactivePaymentMethods, refreshCount, userId])

  const pageTitle = useMemo(() => (
    detail?.user
      ? `${formatUserName(detail.user)} Money`
      : 'User Money'
  ), [detail])
  const draftUserId = draftUserSearch.userId === (userId || '')
    ? draftUserSearch.value
    : userId || ''

  function handleSearch(event) {
    event.preventDefault()

    const nextUserId = draftUserId.trim()
    if (!nextUserId) {
      return
    }

    navigate(`/admin/money/users/${nextUserId}`)
  }

  return (
    <AppPageShell className="admin-page" mainClassName="admin-shell">
      <AdminWorkspaceLayout
        breadcrumbs={['Admin', 'Money', 'User Money']}
        description="Open a user-centered payment, refund, credit, and support summary."
        icon={UserRound}
        title={pageTitle}
      >
        <div className="admin-money-layout">
          <div className="admin-money-toolbar">
            <form className="admin-money-inline-search" onSubmit={handleSearch}>
              <label>
                <span>User ID</span>
                <input
                  value={draftUserId}
                  onChange={(event) => {
                    setDraftUserSearch({
                      userId: userId || '',
                      value: event.target.value,
                    })
                  }}
                />
              </label>
              <button className="admin-money-button" type="submit">
                <Search />
                Open
              </button>
            </form>
            <button
              className="admin-money-button"
              disabled={!userId}
              type="button"
              onClick={() => setRefreshCount((count) => count + 1)}
            >
              <RefreshCw />
              Refresh
            </button>
          </div>

          <label className="admin-money-checkbox admin-money-checkbox--standalone">
            <input
              checked={includeInactivePaymentMethods}
              type="checkbox"
              onChange={(event) => setIncludeInactivePaymentMethods(event.target.checked)}
            />
            <span>Include inactive saved cards</span>
          </label>

          {pageError && (
            <div className="admin-money-alert" role="alert">
              {pageError}
            </div>
          )}

          {loadState === 'idle' && (
            <section className="admin-money-panel">
              <EmptyState>No user selected.</EmptyState>
            </section>
          )}

          {loadState === 'loading' && (
            <section className="admin-money-panel">
              <EmptyState>Loading user money summary.</EmptyState>
            </section>
          )}

          {loadState === 'ready' && detail && (
            <>
              <UserSummary user={detail.user} />
              <PaymentsSection payments={detail.payments ?? []} />
              <RefundsSection refunds={detail.refunds ?? []} />
              <CreditsSection
                creditGrants={detail.credit_grants ?? []}
                creditUsages={detail.credit_usages ?? []}
              />
              <PaymentMethodsSection paymentMethods={detail.payment_methods ?? []} />
              <SupportFlagsSection supportFlags={detail.support_flags ?? []} />
              <AuditSection auditActions={detail.audit_actions ?? []} />
            </>
          )}
        </div>
      </AdminWorkspaceLayout>
    </AppPageShell>
  )
}

export default AdminMoneyUserPage
