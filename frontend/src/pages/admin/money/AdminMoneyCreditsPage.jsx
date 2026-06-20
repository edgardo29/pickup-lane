import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  CircleDollarSign,
  RefreshCw,
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
import { listAdminMoneyCredits } from '../shared/adminApi.js'

const CREDIT_STATUS_OPTIONS = [
  { label: 'All', value: 'all' },
  { label: 'Active', value: 'active' },
  { label: 'Used', value: 'used' },
  { label: 'Reversed', value: 'reversed' },
  { label: 'Expired', value: 'expired' },
]

const EMPTY_FILTERS = {
  sourceBookingId: '',
  sourceGameId: '',
  sourcePaymentId: '',
  userId: '',
}

function AdminMoneyCreditsPage() {
  const { currentUser } = useAuth()
  const [creditStatus, setCreditStatus] = useState('all')
  const [draftFilters, setDraftFilters] = useState(EMPTY_FILTERS)
  const [appliedFilters, setAppliedFilters] = useState(EMPTY_FILTERS)
  const [credits, setCredits] = useState([])
  const [loadState, setLoadState] = useState('loading')
  const [pageError, setPageError] = useState('')
  const [refreshCount, setRefreshCount] = useState(0)

  useEffect(() => {
    let isMounted = true

    async function loadCredits() {
      if (!currentUser) {
        return
      }

      setLoadState('loading')
      setPageError('')

      try {
        const nextCredits = await listAdminMoneyCredits({
          firebaseUser: currentUser,
          creditStatus,
          ...appliedFilters,
        })

        if (!isMounted) {
          return
        }

        setCredits(nextCredits)
        setLoadState('ready')
      } catch (error) {
        if (!isMounted) {
          return
        }

        setCredits([])
        setPageError(error.message || 'Money credits could not be loaded.')
        setLoadState('error')
      }
    }

    loadCredits()

    return () => {
      isMounted = false
    }
  }, [appliedFilters, creditStatus, currentUser, refreshCount])

  const pageTitle = useMemo(() => (
    creditStatus === 'all'
      ? 'Credits'
      : `${formatStatus(creditStatus)} Credits`
  ), [creditStatus])

  function updateDraftFilter(key, value) {
    setDraftFilters((current) => ({
      ...current,
      [key]: value,
    }))
  }

  function handleSearch(event) {
    event.preventDefault()
    setAppliedFilters({
      sourceBookingId: draftFilters.sourceBookingId.trim(),
      sourceGameId: draftFilters.sourceGameId.trim(),
      sourcePaymentId: draftFilters.sourcePaymentId.trim(),
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
            <div className="admin-money-segment" role="group" aria-label="Credit status">
              {CREDIT_STATUS_OPTIONS.map((option) => (
                <button
                  aria-pressed={creditStatus === option.value}
                  className={creditStatus === option.value ? 'is-active' : ''}
                  key={option.value}
                  type="button"
                  onClick={() => setCreditStatus(option.value)}
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
                value={draftFilters.sourceGameId}
                onChange={(event) => updateDraftFilter('sourceGameId', event.target.value)}
              />
            </label>
            <label>
              <span>Booking ID</span>
              <input
                value={draftFilters.sourceBookingId}
                onChange={(event) => updateDraftFilter('sourceBookingId', event.target.value)}
              />
            </label>
            <label>
              <span>Payment ID</span>
              <input
                value={draftFilters.sourcePaymentId}
                onChange={(event) => updateDraftFilter('sourcePaymentId', event.target.value)}
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
              <EmptyState>Loading money credits.</EmptyState>
            </section>
          )}

          {loadState === 'ready' && (
            <section className="admin-money-panel" aria-label="Money credits">
              <SectionHeader
                count={credits.length}
                icon={CircleDollarSign}
                title="Credits"
              />
              {credits.length === 0 ? (
                <EmptyState>No money credits found.</EmptyState>
              ) : (
                <div className="admin-money-row-list">
                  {credits.map((credit) => (
                    <div className="admin-money-row admin-money-row--four" key={credit.id}>
                      <div>
                        <Link className="admin-money-row-link" to={`/admin/money/credits/${credit.id}`}>
                          {formatStatus(credit.credit_status)}
                        </Link>
                        <span>{formatStatus(credit.credit_reason)}</span>
                      </div>
                      <div>
                        <span>{formatMoney(credit.amount_cents, credit.currency)}</span>
                        <span>{formatMoney(credit.remaining_cents, credit.currency)} left</span>
                      </div>
                      <div>
                        <span>User</span>
                        <code>{shortId(credit.user_id)}</code>
                      </div>
                      <div>
                        <span>{formatDateTime(credit.updated_at)}</span>
                        <code>{shortId(credit.id)}</code>
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

export default AdminMoneyCreditsPage
