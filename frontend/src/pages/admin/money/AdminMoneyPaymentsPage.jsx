import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  RefreshCw,
  Search,
  WalletCards,
} from 'lucide-react'
import { AppPageHeader, AppPageShell } from '../../../components/app/index.js'
import { useAuth } from '../../../hooks/useAuth.js'
import '../../../styles/admin/AdminMoneySupport.css'
import {
  EmptyState,
  SectionHeader,
} from './AdminMoneyDetailSections.jsx'
import {
  formatDateTime,
  formatMoney,
  formatStatus,
  shortId,
} from './adminMoneyFormatters.js'
import AdminWorkspaceLayout from '../shared/AdminWorkspaceLayout.jsx'
import { listAdminMoneyPayments } from '../shared/adminApi.js'

const PAYMENT_STATUS_OPTIONS = [
  { label: 'All', value: 'all' },
  { label: 'Requires Payment Method', value: 'requires_payment_method' },
  { label: 'Succeeded', value: 'succeeded' },
  { label: 'Processing', value: 'processing' },
  { label: 'Requires Action', value: 'requires_action' },
  { label: 'Failed', value: 'failed' },
  { label: 'Refunded', value: 'refunded' },
  { label: 'Partial Refund', value: 'partially_refunded' },
  { label: 'Disputed', value: 'disputed' },
  { label: 'Canceled', value: 'canceled' },
]

const EMPTY_FILTERS = {
  bookingId: '',
  gameId: '',
  userId: '',
}

function AdminMoneyPaymentsPage() {
  const { currentUser } = useAuth()
  const [paymentStatus, setPaymentStatus] = useState('all')
  const [draftFilters, setDraftFilters] = useState(EMPTY_FILTERS)
  const [appliedFilters, setAppliedFilters] = useState(EMPTY_FILTERS)
  const [payments, setPayments] = useState([])
  const [loadState, setLoadState] = useState('loading')
  const [pageError, setPageError] = useState('')
  const [refreshCount, setRefreshCount] = useState(0)

  useEffect(() => {
    let isMounted = true

    async function loadPayments() {
      if (!currentUser) {
        return
      }

      setLoadState('loading')
      setPageError('')

      try {
        const nextPayments = await listAdminMoneyPayments({
          firebaseUser: currentUser,
          paymentStatus,
          ...appliedFilters,
        })

        if (!isMounted) {
          return
        }

        setPayments(nextPayments)
        setLoadState('ready')
      } catch (error) {
        if (!isMounted) {
          return
        }

        setPayments([])
        setPageError(error.message || 'Money payments could not be loaded.')
        setLoadState('error')
      }
    }

    loadPayments()

    return () => {
      isMounted = false
    }
  }, [appliedFilters, currentUser, paymentStatus, refreshCount])

  const pageTitle = useMemo(() => (
    paymentStatus === 'all'
      ? 'Payments'
      : `${formatStatus(paymentStatus)} Payments`
  ), [paymentStatus])

  function updateDraftFilter(key, value) {
    setDraftFilters((current) => ({
      ...current,
      [key]: value,
    }))
  }

  function handleSearch(event) {
    event.preventDefault()
    setAppliedFilters({
      bookingId: draftFilters.bookingId.trim(),
      gameId: draftFilters.gameId.trim(),
      userId: draftFilters.userId.trim(),
    })
  }

  return (
    <AppPageShell className="admin-page" mainClassName="admin-shell admin-money-shell">
      <AppPageHeader
        subtitle="Money Support"
        title={pageTitle}
      />

      <AdminWorkspaceLayout>
        <div className="admin-money-layout">
          <div className="admin-money-toolbar">
            <div className="admin-money-segment" role="group" aria-label="Payment status">
              {PAYMENT_STATUS_OPTIONS.map((option) => (
                <button
                  aria-pressed={paymentStatus === option.value}
                  className={paymentStatus === option.value ? 'is-active' : ''}
                  key={option.value}
                  type="button"
                  onClick={() => setPaymentStatus(option.value)}
                >
                  {option.label}
                </button>
              ))}
            </div>
            <button
              className="admin-money-button"
              type="button"
              onClick={() => setRefreshCount((count) => count + 1)}
            >
              <RefreshCw />
              Refresh
            </button>
          </div>

          <form className="admin-money-filters admin-money-filters--payments" onSubmit={handleSearch}>
            <label>
              <span>User ID</span>
              <input
                value={draftFilters.userId}
                onChange={(event) => updateDraftFilter('userId', event.target.value)}
              />
            </label>
            <label>
              <span>Game ID</span>
              <input
                value={draftFilters.gameId}
                onChange={(event) => updateDraftFilter('gameId', event.target.value)}
              />
            </label>
            <label>
              <span>Booking ID</span>
              <input
                value={draftFilters.bookingId}
                onChange={(event) => updateDraftFilter('bookingId', event.target.value)}
              />
            </label>
            <button className="admin-money-button" type="submit">
              <Search />
              Search
            </button>
          </form>

          {pageError && (
            <div className="admin-money-alert" role="alert">
              {pageError}
            </div>
          )}

          {loadState === 'loading' && (
            <section className="admin-money-panel">
              <EmptyState>Loading money payments.</EmptyState>
            </section>
          )}

          {loadState === 'ready' && (
            <section className="admin-money-panel" aria-label="Money payments">
              <SectionHeader
                count={payments.length}
                icon={WalletCards}
                title="Payments"
              />
              {payments.length === 0 ? (
                <EmptyState>No money payments found.</EmptyState>
              ) : (
                <div className="admin-money-row-list">
                  {payments.map((payment) => (
                    <div className="admin-money-row admin-money-row--four" key={payment.id}>
                      <div>
                        <Link className="admin-money-row-link" to={`/admin/money/payments/${payment.id}`}>
                          {formatStatus(payment.payment_status)}
                        </Link>
                        <span>{formatStatus(payment.payment_type)}</span>
                      </div>
                      <div>
                        <span>{formatMoney(payment.amount_cents, payment.currency)}</span>
                        <span>
                          {payment.failure_code
                            ? formatStatus(payment.failure_code)
                            : formatStatus(payment.provider)}
                        </span>
                      </div>
                      <div>
                        <span>User</span>
                        <code>{shortId(payment.payer_user_id)}</code>
                      </div>
                      <div>
                        <span>{formatDateTime(payment.updated_at)}</span>
                        <code>{shortId(payment.id)}</code>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>
          )}
        </div>
      </AdminWorkspaceLayout>
    </AppPageShell>
  )
}

export default AdminMoneyPaymentsPage
