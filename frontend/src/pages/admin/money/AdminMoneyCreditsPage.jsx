import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  CircleDollarSign,
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
import { listAdminMoneyCredits } from '../shared/adminApi.js'

const CREDIT_STATUS_OPTIONS = [
  { label: 'All', value: 'all' },
  { label: 'Active', value: 'active' },
  { label: 'Used', value: 'used' },
  { label: 'Reversed', value: 'reversed' },
]

const EMPTY_FILTERS = {
  creditStatus: 'all',
  query: '',
}

function CreditsEmptyState() {
  return (
    <div className="admin-money-empty-state">
      <span className="admin-money-empty-state__icon">
        <CircleDollarSign />
      </span>
      <div>
        <strong>No money credits found</strong>
        <p>Credit records matching this search will appear here.</p>
      </div>
    </div>
  )
}

function AdminMoneyCreditsPage() {
  const { currentUser } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const querySourceBookingId = searchParams.get('source_booking_id') || ''
  const querySourceGameId = searchParams.get('source_game_id') || ''
  const querySourcePaymentId = searchParams.get('source_payment_id') || ''
  const queryUserId = searchParams.get('user_id') || ''
  const [draftFilters, setDraftFilters] = useState(EMPTY_FILTERS)
  const [appliedFilters, setAppliedFilters] = useState(EMPTY_FILTERS)
  const [credits, setCredits] = useState([])
  const [pageInfo, setPageInfo] = useState({ hasMore: false, nextCursor: '' })
  const [loadState, setLoadState] = useState('loading')
  const [loadMoreState, setLoadMoreState] = useState('idle')
  const [pageError, setPageError] = useState('')

  useEffect(() => {
    let isMounted = true

    async function loadCredits() {
      if (!currentUser) {
        return
      }

      setLoadState('loading')
      setPageError('')

      try {
        const creditPage = await listAdminMoneyCredits({
          firebaseUser: currentUser,
          sourceBookingId: querySourceBookingId,
          sourceGameId: querySourceGameId,
          sourcePaymentId: querySourcePaymentId,
          userId: queryUserId,
          ...appliedFilters,
        })

        if (!isMounted) {
          return
        }

        setCredits(creditPage.items ?? creditPage)
        setPageInfo({
          hasMore: Boolean(creditPage.has_more),
          nextCursor: creditPage.next_cursor || '',
        })
        setLoadState('ready')
      } catch (error) {
        if (!isMounted) {
          return
        }

        setCredits([])
        setPageInfo({ hasMore: false, nextCursor: '' })
        setPageError(error.message || 'Money credits could not be loaded.')
        setLoadState('error')
      }
    }

    loadCredits()

    return () => {
      isMounted = false
    }
  }, [
    appliedFilters,
    currentUser,
    querySourceBookingId,
    querySourceGameId,
    querySourcePaymentId,
    queryUserId,
  ])

  function updateDraftFilter(key, value) {
    setDraftFilters((current) => ({
      ...current,
      [key]: value,
    }))
  }

  function handleSearch(event) {
    event.preventDefault()
    setAppliedFilters({
      creditStatus: draftFilters.creditStatus,
      query: draftFilters.query.trim(),
    })
  }

  function clearDeepLinkFilter(paramName) {
    const nextParams = new URLSearchParams(searchParams)
    nextParams.delete(paramName)
    setSearchParams(nextParams)
  }

  async function handleLoadMore() {
    if (!currentUser || !pageInfo.nextCursor) {
      return
    }

    setLoadMoreState('loading')
    setPageError('')

    try {
      const creditPage = await listAdminMoneyCredits({
        firebaseUser: currentUser,
        cursor: pageInfo.nextCursor,
        sourceBookingId: querySourceBookingId,
        sourceGameId: querySourceGameId,
        sourcePaymentId: querySourcePaymentId,
        userId: queryUserId,
        ...appliedFilters,
      })

      setCredits((current) => [
        ...current,
        ...(creditPage.items ?? creditPage),
      ])
      setPageInfo({
        hasMore: Boolean(creditPage.has_more),
        nextCursor: creditPage.next_cursor || '',
      })
      setLoadMoreState('idle')
    } catch (error) {
      setPageError(error.message || 'More money credits could not be loaded.')
      setLoadMoreState('idle')
    }
  }

  return (
    <>
      <AdminWorkspaceLayout
        breadcrumbs={['Admin', 'Money', 'Credits']}
        description="Search game credits, usage, and reversal context."
        icon={CircleDollarSign}
        title="Credits"
      >
        <div className="admin-money-layout admin-money-layout--credits">
          <form className="admin-money-filters admin-money-filters--credits-ledger" onSubmit={handleSearch}>
            <label>
              <span>Search</span>
              <input
                placeholder="Credit ID, usage ID, user, source payment, booking, or game"
                value={draftFilters.query}
                onChange={(event) => updateDraftFilter('query', event.target.value)}
              />
            </label>
            <label>
              <span>Credit Status</span>
              <select
                value={draftFilters.creditStatus}
                onChange={(event) => updateDraftFilter('creditStatus', event.target.value)}
              >
                {CREDIT_STATUS_OPTIONS.map((option) => (
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

          {(queryUserId
            || querySourceGameId
            || querySourceBookingId
            || querySourcePaymentId) && (
            <div className="admin-money-filter-chips" aria-label="Active credit filters">
              {queryUserId && (
                <button
                  className="admin-money-filter-chip"
                  type="button"
                  onClick={() => clearDeepLinkFilter('user_id')}
                >
                  <span>User: {shortId(queryUserId)}</span>
                  <X />
                </button>
              )}
              {querySourceGameId && (
                <button
                  className="admin-money-filter-chip"
                  type="button"
                  onClick={() => clearDeepLinkFilter('source_game_id')}
                >
                  <span>Source game: {shortId(querySourceGameId)}</span>
                  <X />
                </button>
              )}
              {querySourceBookingId && (
                <button
                  className="admin-money-filter-chip"
                  type="button"
                  onClick={() => clearDeepLinkFilter('source_booking_id')}
                >
                  <span>Source booking: {shortId(querySourceBookingId)}</span>
                  <X />
                </button>
              )}
              {querySourcePaymentId && (
                <button
                  className="admin-money-filter-chip"
                  type="button"
                  onClick={() => clearDeepLinkFilter('source_payment_id')}
                >
                  <span>Source payment: {shortId(querySourcePaymentId)}</span>
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
              <EmptyState>Loading money credits.</EmptyState>
            </section>
          )}

          {loadState === 'ready' && (
            <section className="admin-money-panel" aria-label="Money credits">
              <SectionHeader
                icon={CircleDollarSign}
                meta={`${credits.length} ${credits.length === 1 ? 'credit' : 'credits'}`}
                title="Credits"
              />
              {credits.length === 0 ? (
                <CreditsEmptyState />
              ) : (
                <div className="admin-money-row-list">
                  {credits.map((credit) => (
                    <div className="admin-money-row admin-money-row--four" key={credit.id}>
                      <div>
                        <Link className="admin-money-row-link" to={`/admin/money/credits/${credit.id}`}>
                          Credit {shortId(credit.id)}
                        </Link>
                        <span>{formatStatus(credit.credit_status)}</span>
                      </div>
                      <div>
                        <span>Original {formatMoney(credit.amount_cents, credit.currency)}</span>
                        <span>{formatMoney(credit.available_cents, credit.currency)} available</span>
                        {credit.reserved_cents > 0 && (
                          <span>{formatMoney(credit.reserved_cents, credit.currency)} reserved</span>
                        )}
                      </div>
                      <div>
                        <span>{credit.display?.user_name || credit.display?.user_email || 'No user label'}</span>
                        <span>{credit.display?.context_label || credit.display?.game_label || 'No context'}</span>
                      </div>
                      <div>
                        <span>{formatStatus(credit.credit_reason)}</span>
                        <span>{formatDateTime(credit.created_at)}</span>
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
                        {loadMoreState === 'loading' ? 'Loading' : 'Load More Credits'}
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

export default AdminMoneyCreditsPage
