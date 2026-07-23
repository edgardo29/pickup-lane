import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  Search,
  WalletCards,
  X,
} from 'lucide-react'
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
  { label: 'Canceled', value: 'canceled' },
]

const EMPTY_FILTERS = {
  paymentStatus: 'all',
  paymentType: '',
  query: '',
}

function PaymentsEmptyState() {
  return (
    <div className="admin-money-empty-state">
      <span className="admin-money-empty-state__icon">
        <WalletCards />
      </span>
      <div>
        <strong>No money payments found</strong>
        <p>Payment records matching this search will appear here.</p>
      </div>
    </div>
  )
}

function AdminMoneyPaymentsPage() {
  const { currentUser } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const queryUserId = searchParams.get('user_id') || ''
  const [draftFilters, setDraftFilters] = useState(EMPTY_FILTERS)
  const [appliedFilters, setAppliedFilters] = useState(EMPTY_FILTERS)
  const [payments, setPayments] = useState([])
  const [pageInfo, setPageInfo] = useState({ hasMore: false, nextCursor: '' })
  const [loadState, setLoadState] = useState('loading')
  const [loadMoreState, setLoadMoreState] = useState('idle')
  const [pageError, setPageError] = useState('')

  useEffect(() => {
    let isMounted = true

    async function loadPayments() {
      if (!currentUser) {
        return
      }

      setLoadState('loading')
      setPageError('')

      try {
        const paymentPage = await listAdminMoneyPayments({
          firebaseUser: currentUser,
          userId: queryUserId,
          ...appliedFilters,
        })

        if (!isMounted) {
          return
        }

        setPayments(paymentPage.items ?? paymentPage)
        setPageInfo({
          hasMore: Boolean(paymentPage.has_more),
          nextCursor: paymentPage.next_cursor || '',
        })
        setLoadState('ready')
      } catch (error) {
        if (!isMounted) {
          return
        }

        setPayments([])
        setPageInfo({ hasMore: false, nextCursor: '' })
        setPageError(error.message || 'Money payments could not be loaded.')
        setLoadState('error')
      }
    }

    loadPayments()

    return () => {
      isMounted = false
    }
  }, [appliedFilters, currentUser, queryUserId])

  function updateDraftFilter(key, value) {
    setDraftFilters((current) => ({
      ...current,
      [key]: value,
    }))
  }

  function handleSearch(event) {
    event.preventDefault()
    setAppliedFilters({
      paymentStatus: draftFilters.paymentStatus,
      paymentType: draftFilters.paymentType,
      query: draftFilters.query.trim(),
    })
  }

  function clearUserFilter() {
    const nextParams = new URLSearchParams(searchParams)
    nextParams.delete('user_id')
    setSearchParams(nextParams)
  }

  async function handleLoadMore() {
    if (!currentUser || !pageInfo.nextCursor) {
      return
    }

    setLoadMoreState('loading')
    setPageError('')

    try {
      const paymentPage = await listAdminMoneyPayments({
        firebaseUser: currentUser,
        cursor: pageInfo.nextCursor,
        userId: queryUserId,
        ...appliedFilters,
      })

      setPayments((current) => [
        ...current,
        ...(paymentPage.items ?? paymentPage),
      ])
      setPageInfo({
        hasMore: Boolean(paymentPage.has_more),
        nextCursor: paymentPage.next_cursor || '',
      })
      setLoadMoreState('idle')
    } catch (error) {
      setPageError(error.message || 'More money payments could not be loaded.')
      setLoadMoreState('idle')
    }
  }

  return (
    <>
      <AdminWorkspaceLayout
        breadcrumbs={['Admin', 'Money', 'Payments']}
        description="Search payment records and inspect their current state."
        icon={WalletCards}
        title="Payments"
      >
        <div className="admin-money-layout admin-money-layout--payments">
          <form className="admin-money-filters admin-money-filters--payments-ledger" onSubmit={handleSearch}>
            <label>
              <span>Search</span>
              <input
                placeholder="Payment ID, provider ID, user, booking, or publish fee"
                value={draftFilters.query}
                onChange={(event) => updateDraftFilter('query', event.target.value)}
              />
            </label>
            <label>
              <span>Status</span>
              <select
                value={draftFilters.paymentStatus}
                onChange={(event) => updateDraftFilter('paymentStatus', event.target.value)}
              >
                {PAYMENT_STATUS_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>Payment Type</span>
              <select
                value={draftFilters.paymentType}
                onChange={(event) => updateDraftFilter('paymentType', event.target.value)}
              >
                <option value="">Any type</option>
                <option value="booking">Booking</option>
                <option value="community_publish_fee">Community publish fee</option>
                <option value="admin_charge">Admin charge</option>
              </select>
            </label>
            <button className="admin-money-button" type="submit">
              <Search />
              Search
            </button>
          </form>

          {queryUserId && (
            <div className="admin-money-filter-chips" aria-label="Active payment filters">
              <button
                className="admin-money-filter-chip"
                type="button"
                onClick={clearUserFilter}
              >
                <span>User: {shortId(queryUserId)}</span>
                <X />
              </button>
            </div>
          )}

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
                icon={WalletCards}
                meta={`${payments.length} ${payments.length === 1 ? 'payment' : 'payments'}`}
                title="Payments"
              />
              {payments.length === 0 ? (
                <PaymentsEmptyState />
              ) : (
                <div className="admin-money-row-list">
                  {payments.map((payment) => (
                    <div className="admin-money-row admin-money-row--four" key={payment.id}>
                      <div>
                        <Link className="admin-money-row-link" to={`/admin/money/payments/${payment.id}`}>
                          Payment {shortId(payment.id)}
                        </Link>
                        <span>{formatStatus(payment.payment_status)}</span>
                      </div>
                      <div>
                        <span>{formatMoney(payment.amount_cents, payment.currency)}</span>
                        {payment.is_fully_refunded && <span>Fully refunded</span>}
                      </div>
                      <div>
                        <span>{payment.display?.user_name || payment.display?.user_email || 'No user label'}</span>
                        <span>{payment.display?.context_label || payment.display?.game_label || 'No context'}</span>
                      </div>
                      <div>
                        <span>{formatStatus(payment.payment_type)}</span>
                        <span>{payment.paid_at ? `Paid ${formatDateTime(payment.paid_at)}` : formatDateTime(payment.created_at)}</span>
                      </div>
                    </div>
                  ))}
                  {pageInfo.hasMore && (
                    <div className="admin-money-row">
                      <button
                        className="admin-money-button"
                        disabled={loadMoreState === 'loading'}
                        type="button"
                        onClick={handleLoadMore}
                      >
                        {loadMoreState === 'loading' ? 'Loading' : 'Load More Payments'}
                      </button>
                    </div>
                  )}
                </div>
              )}
            </section>
          )}
        </div>
      </AdminWorkspaceLayout>
    </>
  )
}

export default AdminMoneyPaymentsPage
