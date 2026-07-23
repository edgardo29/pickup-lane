import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  Flag,
  Search,
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
import { listAdminMoneyIssues } from '../shared/adminApi.js'

const ISSUE_STATUS_OPTIONS = [
  { label: 'Open', value: 'open' },
  { label: 'Resolved', value: 'resolved' },
  { label: 'All', value: 'all' },
]
const ISSUE_STATUS_VALUES = new Set(ISSUE_STATUS_OPTIONS.map((option) => option.value))

const EMPTY_FILTERS = {
  issueType: '',
  query: '',
}

const ISSUE_TYPE_OPTIONS = [
  { label: 'Any issue', value: '' },
  { label: 'Refund missing provider reference', value: 'refund_missing_provider_reference' },
  { label: 'Refund processing overdue', value: 'refund_processing_overdue' },
  { label: 'Refund failed', value: 'refund_failed' },
  { label: 'Refund cancelled', value: 'refund_cancelled' },
  { label: 'Refund outcome unknown', value: 'refund_outcome_unknown' },
  { label: 'Credit restore failed', value: 'credit_restore_failed' },
  { label: 'Credit release failed', value: 'credit_release_failed' },
]

function getIssueTypeLabel(issueType) {
  return ISSUE_TYPE_OPTIONS.find((option) => option.value === issueType)?.label
    || formatStatus(issueType)
}

function normalizeIssueStatus(value) {
  return ISSUE_STATUS_VALUES.has(value) ? value : 'open'
}

function issueTarget(issue) {
  if (issue.target_refund_id) {
    return ['Refund', issue.target_refund_id]
  }
  if (issue.target_payment_id) {
    return ['Payment', issue.target_payment_id]
  }
  if (issue.target_game_credit_id) {
    return ['Credit', issue.target_game_credit_id]
  }
  if (issue.target_booking_id) {
    return ['Booking', issue.target_booking_id]
  }
  if (issue.target_game_id) {
    return ['Game', issue.target_game_id]
  }
  return ['User', issue.target_user_id]
}

function issueUserLabel(issue, targetLabel) {
  return issue.display?.user_name
    || issue.display?.user_email
    || targetLabel
}

function issueContextLabel(issue, targetLabel, targetId) {
  return issue.display?.context_label
    || issue.display?.game_label
    || (targetId ? `${targetLabel} ${shortId(targetId)}` : 'No context')
}

function MoneyIssuesEmptyState() {
  return (
    <div className="admin-money-empty-state">
      <span className="admin-money-empty-state__icon">
        <Flag />
      </span>
      <div>
        <strong>No money issues found</strong>
        <p>Issues that need staff attention will appear here.</p>
      </div>
    </div>
  )
}

function AdminMoneyIssuesPage() {
  const { currentUser } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const queryUserId = searchParams.get('user_id') || ''
  const issueStatus = normalizeIssueStatus(searchParams.get('status'))
  const [draftFilters, setDraftFilters] = useState(EMPTY_FILTERS)
  const [appliedFilters, setAppliedFilters] = useState(EMPTY_FILTERS)
  const [moneyIssues, setMoneyIssues] = useState([])
  const [pageInfo, setPageInfo] = useState({ hasMore: false, nextCursor: '' })
  const [loadState, setLoadState] = useState('loading')
  const [loadMoreState, setLoadMoreState] = useState('idle')
  const [pageError, setPageError] = useState('')

  useEffect(() => {
    let isMounted = true

    async function loadMoneyIssues() {
      if (!currentUser) {
        return
      }

      setLoadState('loading')
      setPageError('')

      try {
        const moneyIssuePage = await listAdminMoneyIssues({
          firebaseUser: currentUser,
          issueStatus,
          userId: queryUserId,
          ...appliedFilters,
        })

        if (!isMounted) {
          return
        }

        setMoneyIssues(moneyIssuePage.items ?? moneyIssuePage)
        setPageInfo({
          hasMore: Boolean(moneyIssuePage.has_more),
          nextCursor: moneyIssuePage.next_cursor || '',
        })
        setLoadState('ready')
      } catch (error) {
        if (!isMounted) {
          return
        }

        setMoneyIssues([])
        setPageInfo({ hasMore: false, nextCursor: '' })
        setPageError(error.message || 'Money issues could not be loaded.')
        setLoadState('error')
      }
    }

    loadMoneyIssues()

    return () => {
      isMounted = false
    }
  }, [appliedFilters, currentUser, issueStatus, queryUserId])

  function updateDraftFilter(key, value) {
    setDraftFilters((current) => ({
      ...current,
      [key]: value,
    }))
  }

  function handleSearch(event) {
    event.preventDefault()
    setAppliedFilters({
      issueType: draftFilters.issueType.trim(),
      query: draftFilters.query.trim(),
    })
  }

  function handleStatusChange(nextStatus) {
    const nextParams = new URLSearchParams(searchParams)
    if (nextStatus === 'open') {
      nextParams.delete('status')
    } else {
      nextParams.set('status', nextStatus)
    }
    setSearchParams(nextParams)
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
      const moneyIssuePage = await listAdminMoneyIssues({
        firebaseUser: currentUser,
        issueStatus,
        cursor: pageInfo.nextCursor,
        userId: queryUserId,
        ...appliedFilters,
      })

      setMoneyIssues((current) => [
        ...current,
        ...(moneyIssuePage.items ?? moneyIssuePage),
      ])
      setPageInfo({
        hasMore: Boolean(moneyIssuePage.has_more),
        nextCursor: moneyIssuePage.next_cursor || '',
      })
      setLoadMoreState('idle')
    } catch (error) {
      setPageError(error.message || 'More money issues could not be loaded.')
      setLoadMoreState('idle')
    }
  }

  return (
    <AdminWorkspaceLayout
      breadcrumbs={['Admin', 'Money', 'Money Issues']}
      description="Review money problems that need staff attention."
      icon={Flag}
      title="Money Issues"
    >
      <div className="admin-money-layout admin-money-layout--issues">
        <div className="admin-money-toolbar">
          <div className="app-tabs admin-money-tabs" role="group" aria-label="Issue status">
            {ISSUE_STATUS_OPTIONS.map((option) => (
              <button
                aria-pressed={issueStatus === option.value}
                className={issueStatus === option.value ? 'active' : ''}
                key={option.value}
                type="button"
                onClick={() => handleStatusChange(option.value)}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>

        <form className="admin-money-filters admin-money-filters--issues" onSubmit={handleSearch}>
          <label>
            <span>Search</span>
            <input
              placeholder="Issue ID, operation key, user name, or email"
              value={draftFilters.query}
              onChange={(event) => updateDraftFilter('query', event.target.value)}
            />
          </label>
          <label>
            <span>Issue Type</span>
            <select
              value={draftFilters.issueType}
              onChange={(event) => updateDraftFilter('issueType', event.target.value)}
            >
              {ISSUE_TYPE_OPTIONS.map((option) => (
                <option key={option.value || 'all'} value={option.value}>
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

        {(queryUserId || appliedFilters.issueType || appliedFilters.query) && (
          <div className="admin-money-filter-chips" aria-label="Active issue filters">
            {queryUserId && (
              <button
                className="admin-money-filter-chip"
                type="button"
                onClick={clearUserFilter}
              >
                User: {shortId(queryUserId)}
              </button>
            )}
            {appliedFilters.issueType && (
              <button
                className="admin-money-filter-chip"
                type="button"
                onClick={() => {
                  setDraftFilters((current) => ({ ...current, issueType: '' }))
                  setAppliedFilters((current) => ({ ...current, issueType: '' }))
                }}
              >
                Type: {getIssueTypeLabel(appliedFilters.issueType)}
              </button>
            )}
            {appliedFilters.query && (
              <button
                className="admin-money-filter-chip"
                type="button"
                onClick={() => {
                  setDraftFilters((current) => ({ ...current, query: '' }))
                  setAppliedFilters((current) => ({ ...current, query: '' }))
                }}
              >
                Search: {appliedFilters.query}
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
            <EmptyState>Loading money issues.</EmptyState>
          </section>
        )}

        {loadState === 'ready' && (
          <section className="admin-money-panel" aria-label="Money issues">
            <SectionHeader
              icon={Flag}
              meta={`${moneyIssues.length} ${moneyIssues.length === 1 ? 'issue' : 'issues'}`}
              title="Money Issues"
            />
            {moneyIssues.length === 0 ? (
              <MoneyIssuesEmptyState />
            ) : (
              <div className="admin-money-row-list">
                {moneyIssues.map((issue) => {
                  const [targetLabel, targetId] = issueTarget(issue)

                  return (
                    <div className="admin-money-row admin-money-row--four" key={issue.id}>
                      <div>
                        <Link className="admin-money-row-link" to={`/admin/money/issues/${issue.id}`}>
                          {formatStatus(issue.issue_type)}
                        </Link>
                        <span>{issue.latest_summary || formatStatus(issue.latest_reason_code)}</span>
                      </div>
                      <div>
                        <span>{formatMoney(issue.amount_cents, issue.currency)}</span>
                        <span>{formatStatus(issue.origin_workflow)}</span>
                      </div>
                      <div>
                        <span>{issueUserLabel(issue, targetLabel)}</span>
                        <span>{issueContextLabel(issue, targetLabel, targetId)}</span>
                      </div>
                      <div>
                        <span>{formatStatus(issue.recommended_action_code)}</span>
                        <span>{formatDateTime(issue.last_activity_at || issue.last_detected_at)}</span>
                      </div>
                    </div>
                  )
                })}
                {pageInfo.hasMore && (
                  <div className="admin-money-row">
                    <button
                      className="admin-money-button"
                      disabled={loadMoreState === 'loading'}
                      type="button"
                      onClick={handleLoadMore}
                    >
                      {loadMoreState === 'loading' ? 'Loading' : 'Load More Issues'}
                    </button>
                  </div>
                )}
              </div>
            )}
          </section>
        )}
      </div>
    </AdminWorkspaceLayout>
  )
}

export default AdminMoneyIssuesPage
