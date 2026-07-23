import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  CircleDollarSign,
  CreditCard,
  Search,
  UserRound,
} from 'lucide-react'
import { useAuth } from '../../../hooks/useAuth.js'
import '../../../styles/admin/AdminMoneySupport.css'
import {
  DetailCodeField,
  DetailField,
  EmptyState,
  MoneyIssuesSection,
  PaymentsSection,
  RefundsSection,
  SectionHeader,
} from './AdminMoneyDetailSections.jsx'
import {
  formatDateTime,
  formatMoney,
  formatStatus,
  shortId,
} from './adminMoneyFormatters.js'
import AdminWorkspaceLayout from '../shared/AdminWorkspaceLayout.jsx'
import { getAdminMoneyUser, listAdminUsers } from '../shared/adminApi.js'

const USER_SEARCH_LIMIT = 5

function formatUserName(user) {
  return user?.name || user?.email || 'User'
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
          <span>Email</span>
          <strong>{user.email || 'No email'}</strong>
        </div>
        <div>
          <span>Account</span>
          <strong>{formatStatus(user.account_status)}</strong>
        </div>
        <div>
          <span>User Detail</span>
          <strong>
            <Link className="admin-money-link" to={`/admin/users/${user.id}`}>
              Open
            </Link>
          </strong>
        </div>
      </div>
      <div className="admin-money-field-grid">
        <DetailCodeField label="User ID" value={user.id} />
        <DetailField label="Created" value={formatDateTime(user.created_at)} />
      </div>
    </section>
  )
}

function SnapshotSection({ snapshot }) {
  return (
    <section className="admin-money-panel" aria-label="User money snapshot">
      <SectionHeader icon={CircleDollarSign} title="Snapshot" />
      <div className="admin-money-kpis">
        <div>
          <span>Available Credit</span>
          <strong>{formatMoney(snapshot.available_credit_cents, snapshot.currency)}</strong>
        </div>
        <div>
          <span>Open Money Issues</span>
          <strong>{snapshot.open_money_issue_count}</strong>
        </div>
      </div>
    </section>
  )
}

function SavedCardsSection({
  activeCount,
  hasMore,
  isLoadingMore,
  onLoadMore,
  paymentMethods,
}) {
  return (
    <section className="admin-money-panel" aria-label="Saved cards">
      <SectionHeader count={activeCount} icon={CreditCard} title="Saved Cards" />
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
                <span>Detached {formatDateTime(method.detached_at)}</span>
              </div>
              <div>
                <span>Updated {formatDateTime(method.updated_at)}</span>
                <code>{shortId(method.id)}</code>
              </div>
            </div>
          ))}
          {hasMore && (
            <div className="admin-money-row">
              <button
                className="admin-money-button"
                disabled={isLoadingMore}
                type="button"
                onClick={onLoadMore}
              >
                {isLoadingMore ? 'Loading' : 'Load More Saved Cards'}
              </button>
            </div>
          )}
        </div>
      )}
    </section>
  )
}

function UserSearchResultsSection({
  error,
  hasMore,
  searchState,
  users,
}) {
  return (
    <section className="admin-money-panel" aria-label="User search results">
      <SectionHeader count={users.length} icon={Search} title="User Search" />
      {searchState === 'loading' && (
        <EmptyState>Loading users.</EmptyState>
      )}
      {error && (
        <div className="admin-money-alert" role="alert">
          {error}
        </div>
      )}
      {searchState === 'ready' && users.length === 0 && (
        <EmptyState>No users found.</EmptyState>
      )}
      {users.length > 0 && (
        <div className="admin-money-row-list">
          {users.map((user) => (
            <div className="admin-money-row admin-money-row--four" key={user.id}>
              <div>
                <Link className="admin-money-row-link" to={`/admin/money/users/${user.id}`}>
                  {user.display_name || user.email || 'User'}
                </Link>
                <span>{user.email || 'No email'}</span>
              </div>
              <div>
                <span>{formatStatus(user.account_status)}</span>
                <span>{formatStatus(user.role)}</span>
              </div>
              <div>
                <span>{formatStatus(user.hosting_status || 'not_eligible')}</span>
                <span>{formatDateTime(user.member_since)}</span>
              </div>
              <div>
                <code>{shortId(user.id)}</code>
              </div>
            </div>
          ))}
          {hasMore && (
            <div className="admin-money-row">
              <Link className="admin-money-row-link" to="/admin/users">More in User Directory</Link>
            </div>
          )}
        </div>
      )}
    </section>
  )
}

function UserMoneyLandingState() {
  return (
    <section className="admin-money-panel">
      <div className="admin-money-empty-state">
        <span className="admin-money-empty-state__icon">
          <UserRound />
        </span>
        <div>
          <strong>Select a user</strong>
          <p>Search by name, email, or user ID to open a money snapshot.</p>
          <Link className="admin-money-button" to="/admin/users">
            <Search />
            User Directory
          </Link>
        </div>
      </div>
    </section>
  )
}

function AdminMoneyUserPage() {
  const { userId } = useParams()
  const { currentUser } = useAuth()
  const [userSearchQuery, setUserSearchQuery] = useState(userId || '')
  const [userSearchResults, setUserSearchResults] = useState([])
  const [userSearchState, setUserSearchState] = useState('idle')
  const [userSearchError, setUserSearchError] = useState('')
  const [userSearchHasMore, setUserSearchHasMore] = useState(false)
  const [includeInactivePaymentMethods, setIncludeInactivePaymentMethods] = useState(false)
  const [detail, setDetail] = useState(null)
  const [loadState, setLoadState] = useState(userId ? 'loading' : 'idle')
  const [pageError, setPageError] = useState('')
  const [savedCardsLoadState, setSavedCardsLoadState] = useState('idle')

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
          savedCardsCursor: '',
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
  }, [currentUser, includeInactivePaymentMethods, userId])

  const userFilterQuery = userId ? `?user_id=${encodeURIComponent(userId)}` : ''

  async function handleSearch(event) {
    event.preventDefault()

    const query = userSearchQuery.trim()
    if (!query || !currentUser) {
      return
    }

    setUserSearchState('loading')
    setUserSearchError('')
    setUserSearchResults([])
    setUserSearchHasMore(false)

    try {
      const response = await listAdminUsers({
        firebaseUser: currentUser,
        limit: USER_SEARCH_LIMIT,
        query,
      })
      setUserSearchResults(response.users ?? [])
      setUserSearchHasMore(Boolean(response.has_more))
      setUserSearchState('ready')
    } catch (error) {
      setUserSearchError(error.message || 'Users could not be searched.')
      setUserSearchState('error')
    }
  }

  async function handleLoadMoreSavedCards() {
    const nextCursor = detail?.saved_cards?.next_cursor
    if (!currentUser || !userId || !nextCursor) {
      return
    }

    setSavedCardsLoadState('loading')
    setPageError('')

    try {
      const nextDetail = await getAdminMoneyUser({
        firebaseUser: currentUser,
        includeInactivePaymentMethods,
        savedCardsCursor: nextCursor,
        userId,
      })

      setDetail((current) => ({
        ...nextDetail,
        saved_cards: {
          ...nextDetail.saved_cards,
          items: [
            ...(current?.saved_cards?.items ?? []),
            ...(nextDetail.saved_cards?.items ?? []),
          ],
        },
      }))
      setSavedCardsLoadState('idle')
    } catch (error) {
      setPageError(error.message || 'More saved cards could not be loaded.')
      setSavedCardsLoadState('idle')
    }
  }

  return (
    <AdminWorkspaceLayout
      breadcrumbs={['Admin', 'Money', 'User Money']}
      description="Open a user-centered money snapshot and links to detailed ledgers."
      icon={UserRound}
      title="User Money"
    >
      <div className="admin-money-layout admin-money-layout--user">
        <div className="admin-money-toolbar">
          <form className="admin-money-inline-search" onSubmit={handleSearch}>
            <label>
              <span>User</span>
              <input
                value={userSearchQuery}
                onChange={(event) => setUserSearchQuery(event.target.value)}
              />
            </label>
            <button className="admin-money-button" type="submit">
              <Search />
              Search
            </button>
          </form>
        </div>

        {loadState === 'ready' && detail && (
          <label className="admin-money-checkbox admin-money-checkbox--standalone">
            <input
              checked={includeInactivePaymentMethods}
              type="checkbox"
              onChange={(event) => setIncludeInactivePaymentMethods(event.target.checked)}
            />
            <span>Include inactive saved cards</span>
          </label>
        )}

        {pageError && (
          <div className="admin-money-alert" role="alert">
            {pageError}
          </div>
        )}

        {userSearchState !== 'idle' && (
          <UserSearchResultsSection
            error={userSearchError}
            hasMore={userSearchHasMore}
            searchState={userSearchState}
            users={userSearchResults}
          />
        )}

        {loadState === 'idle' && userSearchState === 'idle' && (
          <UserMoneyLandingState />
        )}

        {loadState === 'loading' && (
          <section className="admin-money-panel">
            <EmptyState>Loading user money summary.</EmptyState>
          </section>
        )}

        {loadState === 'ready' && detail && (
          <>
            <UserSummary user={detail.user} />
            <SnapshotSection snapshot={detail.snapshot} />
            <MoneyIssuesSection
              hasMore={detail.open_money_issues?.has_more}
              moneyIssues={detail.open_money_issues?.items ?? []}
              viewAllTo={`/admin/money/issues?status=open&user_id=${encodeURIComponent(userId)}`}
            />
            <SavedCardsSection
              activeCount={detail.saved_cards?.active_count ?? 0}
              hasMore={detail.saved_cards?.has_more}
              isLoadingMore={savedCardsLoadState === 'loading'}
              paymentMethods={detail.saved_cards?.items ?? []}
              onLoadMore={handleLoadMoreSavedCards}
            />
            <PaymentsSection
              hasMore={detail.recent_payments?.has_more}
              payments={detail.recent_payments?.items ?? []}
              showIssueContext={false}
              viewAllTo={`/admin/money/payments${userFilterQuery}`}
            />
            <RefundsSection
              hasMore={detail.recent_refunds?.has_more}
              refunds={detail.recent_refunds?.items ?? []}
              showIssueContext={false}
              viewAllTo={`/admin/money/refunds${userFilterQuery}`}
            />
            <CreditPreviewSection
              hasMore={detail.recent_credits?.has_more}
              credits={detail.recent_credits?.items ?? []}
              viewAllTo={`/admin/money/credits${userFilterQuery}`}
            />
          </>
        )}
      </div>
    </AdminWorkspaceLayout>
  )
}

function CreditPreviewSection({ credits, hasMore, viewAllTo }) {
  return (
    <section className="admin-money-panel" aria-label="Recent credits">
      <SectionHeader count={credits.length} icon={CircleDollarSign} title="Credits" />
      {credits.length === 0 ? (
        <EmptyState>No credits linked here.</EmptyState>
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
                <span>{formatMoney(credit.available_cents, credit.currency)} available</span>
              </div>
              <div>
                <span>{credit.context_label || 'No source context'}</span>
                <code>
                  {shortId(
                    credit.source_booking_id
                      || credit.source_game_id
                      || credit.source_payment_id,
                  )}
                </code>
              </div>
              <div>
                <span>{formatDateTime(credit.created_at)}</span>
                <code>{shortId(credit.id)}</code>
              </div>
            </div>
          ))}
          {hasMore && viewAllTo && (
            <div className="admin-money-row">
              <Link className="admin-money-row-link" to={viewAllTo}>View all credits</Link>
            </div>
          )}
        </div>
      )}
    </section>
  )
}

export default AdminMoneyUserPage
