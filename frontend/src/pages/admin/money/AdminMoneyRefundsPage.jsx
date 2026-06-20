import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  RefreshCw,
  RotateCcw,
  Search,
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
import { listAdminMoneyRefunds } from '../shared/adminApi.js'

const REFUND_STATUS_OPTIONS = [
  { label: 'All', value: 'all' },
  { label: 'Pending', value: 'pending' },
  { label: 'Approved', value: 'approved' },
  { label: 'Processing', value: 'processing' },
  { label: 'Succeeded', value: 'succeeded' },
  { label: 'Failed', value: 'failed' },
  { label: 'Cancelled', value: 'cancelled' },
]

const EMPTY_FILTERS = {
  bookingId: '',
  gameId: '',
  paymentId: '',
  userId: '',
}

function AdminMoneyRefundsPage() {
  const { currentUser } = useAuth()
  const [refundStatus, setRefundStatus] = useState('all')
  const [draftFilters, setDraftFilters] = useState(EMPTY_FILTERS)
  const [appliedFilters, setAppliedFilters] = useState(EMPTY_FILTERS)
  const [refunds, setRefunds] = useState([])
  const [loadState, setLoadState] = useState('loading')
  const [pageError, setPageError] = useState('')
  const [refreshCount, setRefreshCount] = useState(0)

  useEffect(() => {
    let isMounted = true

    async function loadRefunds() {
      if (!currentUser) {
        return
      }

      setLoadState('loading')
      setPageError('')

      try {
        const nextRefunds = await listAdminMoneyRefunds({
          firebaseUser: currentUser,
          refundStatus,
          ...appliedFilters,
        })

        if (!isMounted) {
          return
        }

        setRefunds(nextRefunds)
        setLoadState('ready')
      } catch (error) {
        if (!isMounted) {
          return
        }

        setRefunds([])
        setPageError(error.message || 'Money refunds could not be loaded.')
        setLoadState('error')
      }
    }

    loadRefunds()

    return () => {
      isMounted = false
    }
  }, [appliedFilters, currentUser, refreshCount, refundStatus])

  const pageTitle = useMemo(() => (
    refundStatus === 'all'
      ? 'Refunds'
      : `${formatStatus(refundStatus)} Refunds`
  ), [refundStatus])

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
      paymentId: draftFilters.paymentId.trim(),
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
            <div className="admin-money-segment" role="group" aria-label="Refund status">
              {REFUND_STATUS_OPTIONS.map((option) => (
                <button
                  aria-pressed={refundStatus === option.value}
                  className={refundStatus === option.value ? 'is-active' : ''}
                  key={option.value}
                  type="button"
                  onClick={() => setRefundStatus(option.value)}
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

          <form className="admin-money-filters" onSubmit={handleSearch}>
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
            <label>
              <span>Payment ID</span>
              <input
                value={draftFilters.paymentId}
                onChange={(event) => updateDraftFilter('paymentId', event.target.value)}
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
              <EmptyState>Loading money refunds.</EmptyState>
            </section>
          )}

          {loadState === 'ready' && (
            <section className="admin-money-panel" aria-label="Money refunds">
              <SectionHeader
                count={refunds.length}
                icon={RotateCcw}
                title="Refunds"
              />
              {refunds.length === 0 ? (
                <EmptyState>No money refunds found.</EmptyState>
              ) : (
                <div className="admin-money-row-list">
                  {refunds.map((refund) => (
                    <div className="admin-money-row admin-money-row--four" key={refund.id}>
                      <div>
                        <Link className="admin-money-row-link" to={`/admin/money/refunds/${refund.id}`}>
                          {formatStatus(refund.refund_status)}
                        </Link>
                        <span>{formatStatus(refund.refund_reason)}</span>
                      </div>
                      <div>
                        <span>{formatMoney(refund.amount_cents, refund.currency)}</span>
                        <span>{refund.booking_id ? 'Booking refund' : 'Participant refund'}</span>
                      </div>
                      <div>
                        <span>Payment</span>
                        <code>{shortId(refund.payment_id)}</code>
                      </div>
                      <div>
                        <span>{formatDateTime(refund.updated_at)}</span>
                        <code>{shortId(refund.id)}</code>
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

export default AdminMoneyRefundsPage
