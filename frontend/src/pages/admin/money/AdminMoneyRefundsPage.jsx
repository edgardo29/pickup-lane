import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  RotateCcw,
  Search,
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
  query: '',
  refundStatus: 'all',
}

function getRefundScopeLabel(refund) {
  if (refund.host_publish_fee_id) {
    return 'Publish fee refund'
  }
  if (refund.participant_id) {
    return 'Participant refund'
  }
  return 'Booking refund'
}

function RefundsEmptyState() {
  return (
    <div className="admin-money-empty-state">
      <span className="admin-money-empty-state__icon">
        <RotateCcw />
      </span>
      <div>
        <strong>No money refunds found</strong>
        <p>Refund records matching this search will appear here.</p>
      </div>
    </div>
  )
}

function AdminMoneyRefundsPage() {
  const { currentUser } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const queryUserId = searchParams.get('user_id') || ''
  const queryPaymentId = searchParams.get('payment_id') || ''
  const [draftFilters, setDraftFilters] = useState(EMPTY_FILTERS)
  const [appliedFilters, setAppliedFilters] = useState(EMPTY_FILTERS)
  const [refunds, setRefunds] = useState([])
  const [pageInfo, setPageInfo] = useState({ hasMore: false, nextCursor: '' })
  const [loadState, setLoadState] = useState('loading')
  const [loadMoreState, setLoadMoreState] = useState('idle')
  const [pageError, setPageError] = useState('')

  useEffect(() => {
    let isMounted = true

    async function loadRefunds() {
      if (!currentUser) {
        return
      }

      setLoadState('loading')
      setPageError('')

      try {
        const refundPage = await listAdminMoneyRefunds({
          firebaseUser: currentUser,
          paymentId: queryPaymentId,
          userId: queryUserId,
          ...appliedFilters,
        })

        if (!isMounted) {
          return
        }

        setRefunds(refundPage.items ?? refundPage)
        setPageInfo({
          hasMore: Boolean(refundPage.has_more),
          nextCursor: refundPage.next_cursor || '',
        })
        setLoadState('ready')
      } catch (error) {
        if (!isMounted) {
          return
        }

        setRefunds([])
        setPageInfo({ hasMore: false, nextCursor: '' })
        setPageError(error.message || 'Money refunds could not be loaded.')
        setLoadState('error')
      }
    }

    loadRefunds()

    return () => {
      isMounted = false
    }
  }, [appliedFilters, currentUser, queryPaymentId, queryUserId])

  function updateDraftFilter(key, value) {
    setDraftFilters((current) => ({
      ...current,
      [key]: value,
    }))
  }

  function handleSearch(event) {
    event.preventDefault()
    setAppliedFilters({
      query: draftFilters.query.trim(),
      refundStatus: draftFilters.refundStatus,
    })
  }

  function clearDeepLinkFilter(key) {
    const nextParams = new URLSearchParams(searchParams)
    nextParams.delete(key === 'paymentId' ? 'payment_id' : 'user_id')
    setSearchParams(nextParams)
  }

  async function handleLoadMore() {
    if (!currentUser || !pageInfo.nextCursor) {
      return
    }

    setLoadMoreState('loading')
    setPageError('')

    try {
      const refundPage = await listAdminMoneyRefunds({
        firebaseUser: currentUser,
        cursor: pageInfo.nextCursor,
        paymentId: queryPaymentId,
        userId: queryUserId,
        ...appliedFilters,
      })

      setRefunds((current) => [
        ...current,
        ...(refundPage.items ?? refundPage),
      ])
      setPageInfo({
        hasMore: Boolean(refundPage.has_more),
        nextCursor: refundPage.next_cursor || '',
      })
      setLoadMoreState('idle')
    } catch (error) {
      setPageError(error.message || 'More money refunds could not be loaded.')
      setLoadMoreState('idle')
    }
  }

  return (
    <>
      <AdminWorkspaceLayout
        breadcrumbs={['Admin', 'Money', 'Refunds']}
        description="Search refund records and inspect processing outcomes."
        icon={RotateCcw}
        title="Refunds"
      >
        <div className="admin-money-layout admin-money-layout--refunds">
          <form className="admin-money-filters admin-money-filters--refunds-ledger" onSubmit={handleSearch}>
            <label>
              <span>Search</span>
              <input
                placeholder="Refund ID, provider ID, user, payment, or booking"
                value={draftFilters.query}
                onChange={(event) => updateDraftFilter('query', event.target.value)}
              />
            </label>
            <label>
              <span>Refund Status</span>
              <select
                value={draftFilters.refundStatus}
                onChange={(event) => updateDraftFilter('refundStatus', event.target.value)}
              >
                {REFUND_STATUS_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <button className="admin-money-button" type="submit">
              <Search />
              Search
            </button>
          </form>
          {(queryUserId || queryPaymentId) && (
            <div className="admin-money-filter-chips" aria-label="Active refund filters">
              {queryUserId && (
                <button
                  className="admin-money-filter-chip"
                  type="button"
                  onClick={() => clearDeepLinkFilter('userId')}
                >
                  <span>User: {shortId(queryUserId)}</span>
                  <X />
                </button>
              )}
              {queryPaymentId && (
                <button
                  className="admin-money-filter-chip"
                  type="button"
                  onClick={() => clearDeepLinkFilter('paymentId')}
                >
                  <span>Payment: {shortId(queryPaymentId)}</span>
                  <X />
                </button>
              )}
            </div>
          )}

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
                icon={RotateCcw}
                meta={`${refunds.length} ${refunds.length === 1 ? 'refund' : 'refunds'}`}
                title="Refunds"
              />
              {refunds.length === 0 ? (
                <RefundsEmptyState />
              ) : (
                <div className="admin-money-row-list">
                  {refunds.map((refund) => (
                    <div className="admin-money-row admin-money-row--four" key={refund.id}>
                      <div>
                        <Link className="admin-money-row-link" to={`/admin/money/refunds/${refund.id}`}>
                          Refund {shortId(refund.id)}
                        </Link>
                        <span>{formatStatus(refund.refund_status)}</span>
                      </div>
                      <div>
                        <span>{formatMoney(refund.amount_cents, refund.currency)}</span>
                        <span>{formatStatus(refund.refund_reason)}</span>
                      </div>
                      <div>
                        <span>{refund.display?.user_name || refund.display?.user_email || 'No user label'}</span>
                        <span>{refund.display?.context_label || getRefundScopeLabel(refund)}</span>
                      </div>
                      <div>
                        <span>{formatDateTime(refund.created_at)}</span>
                        {refund.linked_issue && <span>Open money issue</span>}
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
                        {loadMoreState === 'loading' ? 'Loading' : 'Load More Refunds'}
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

export default AdminMoneyRefundsPage
