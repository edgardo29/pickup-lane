import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ClipboardList,
  SearchCheck,
} from 'lucide-react'
import { FormErrorMessage } from '../../../components/FormErrorMessage.jsx'
import { useAuth } from '../../../hooks/useAuth.js'
import '../../../styles/admin/AdminReviewCases.css'
import AdminWorkspaceLayout from '../shared/AdminWorkspaceLayout.jsx'
import { listAdminReviewCases } from '../shared/adminApi.js'
import {
  formatAdminReviewClosed,
  formatAdminReviewClosureDetail,
  formatAdminReviewFindingDetail,
  formatAdminReviewTargetTypeWithStatus,
  formatAdminReviewUpdated,
  getAdminReviewFindingCountParts,
} from './adminReviewFormatters.js'

const PAGE_SIZE = 24
const DEFAULT_CASE_STATUS = 'open'
const DEFAULT_TARGET_TYPE = 'content_targets'
const CASE_STATUS_TABS = [
  { label: 'Open', value: 'open' },
  { label: 'Closed', value: 'closed' },
]

function ReviewCaseCard({ reviewCase }) {
  const findingCount = getAdminReviewFindingCountParts(reviewCase)
  const isClosed = reviewCase.case_status === 'closed'

  return (
    <Link
      className="admin-review-card"
      to={`/admin/review-cases/${reviewCase.id}`}
    >
      <header className="admin-review-card__header">
        <span>{formatAdminReviewTargetTypeWithStatus(reviewCase)}</span>
      </header>
      <div className="admin-review-card__body">
        <div className="admin-review-card__finding">
          <span className="admin-review-card__count">
            {findingCount.count}
          </span>
          <div>
            <span className="admin-review-card__summary-label">
              {findingCount.label}
            </span>
            <span className="admin-review-card__issues">
              {isClosed
                ? formatAdminReviewClosureDetail(reviewCase)
                : formatAdminReviewFindingDetail(reviewCase)}
            </span>
          </div>
        </div>
      </div>
      <footer className="admin-review-card__footer">
        <span>
          {isClosed
            ? formatAdminReviewClosed(reviewCase.closed_at)
            : formatAdminReviewUpdated(reviewCase.updated_at)}
        </span>
      </footer>
    </Link>
  )
}

function AdminReviewCasesPage() {
  const { currentUser } = useAuth()
  const [cases, setCases] = useState([])
  const [nextCursor, setNextCursor] = useState('')
  const [hasMoreCases, setHasMoreCases] = useState(false)
  const [isLoadingMore, setIsLoadingMore] = useState(false)
  const [loadState, setLoadState] = useState('loading')
  const [pageError, setPageError] = useState('')
  const [loadMoreError, setLoadMoreError] = useState('')
  const [caseStatus, setCaseStatus] = useState(DEFAULT_CASE_STATUS)
  const requestIdRef = useRef(0)

  useEffect(() => {
    let isMounted = true
    const requestId = requestIdRef.current + 1
    requestIdRef.current = requestId

    async function loadCases() {
      if (!currentUser) return
      setLoadState('loading')
      setCases([])
      setPageError('')
      setLoadMoreError('')
      setNextCursor('')
      setHasMoreCases(false)

      try {
        const response = await listAdminReviewCases({
          caseCategory: 'content_moderation',
          caseStatus,
          firebaseUser: currentUser,
          limit: PAGE_SIZE,
          targetType: DEFAULT_TARGET_TYPE,
        })
        if (!isMounted || requestId !== requestIdRef.current) return
        const nextCases = response.cases ?? []
        setCases(nextCases)
        setNextCursor(response.next_cursor ?? '')
        setHasMoreCases(Boolean(response.has_more))
        setLoadState('ready')
      } catch (error) {
        if (!isMounted || requestId !== requestIdRef.current) return
        setCases([])
        setNextCursor('')
        setHasMoreCases(false)
        setPageError(error.message || 'Review cases could not be loaded.')
        setLoadState('error')
      }
    }

    loadCases()
    return () => {
      isMounted = false
    }
  }, [caseStatus, currentUser])

  async function loadMoreCases() {
    if (!currentUser || isLoadingMore || !hasMoreCases || !nextCursor) {
      return
    }

    setIsLoadingMore(true)
    setLoadMoreError('')
    const requestId = requestIdRef.current

    try {
      const response = await listAdminReviewCases({
        caseCategory: 'content_moderation',
        caseStatus,
        cursor: nextCursor,
        firebaseUser: currentUser,
        limit: PAGE_SIZE,
        targetType: DEFAULT_TARGET_TYPE,
      })

      if (requestId !== requestIdRef.current) return

      const nextCases = response.cases ?? []
      setCases((currentCases) => [...currentCases, ...nextCases])
      setNextCursor(response.next_cursor ?? '')
      setHasMoreCases(Boolean(response.has_more))
    } catch (error) {
      if (requestId !== requestIdRef.current) return
      setLoadMoreError(error.message || 'More review cases could not be loaded.')
    } finally {
      if (requestId === requestIdRef.current) {
        setIsLoadingMore(false)
      }
    }
  }

  return (
    <AdminWorkspaceLayout
      breadcrumbs={['Admin', 'Review Cases']}
      description="Inspect internal review work and close cases after post or game actions are complete."
      icon={SearchCheck}
      title="Review Cases"
    >
      <div className="admin-review-layout">
        {pageError && (
          <FormErrorMessage className="admin-review-page-error">
            {pageError}
          </FormErrorMessage>
        )}

        <div className="admin-review-tabs" role="tablist" aria-label="Review case status">
          {CASE_STATUS_TABS.map((tab) => (
            <button
              key={tab.value}
              aria-selected={caseStatus === tab.value}
              className="admin-review-tabs__button"
              role="tab"
              type="button"
              onClick={() => setCaseStatus(tab.value)}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <section className="admin-review-case-board" aria-label="Review cases">
          {loadState === 'loading' && <p className="admin-review-empty">Loading review cases.</p>}
          {loadState === 'ready' && !cases.length && (
            <div className="admin-review-empty-state">
              <ClipboardList />
              <strong>No review cases</strong>
              <span>This view has no matching internal review work.</span>
            </div>
          )}
          {loadState === 'ready' && cases.length > 0 && (
            <div className="admin-review-card-grid">
              {cases.map((reviewCase) => (
                <ReviewCaseCard key={reviewCase.id} reviewCase={reviewCase} />
              ))}
            </div>
          )}
        </section>

        {loadMoreError && (
          <FormErrorMessage className="admin-review-page-error">
            {loadMoreError}
          </FormErrorMessage>
        )}

        {loadState === 'ready' && hasMoreCases && (
          <div className="admin-review-load-more">
            <button
              className="admin-review-button"
              disabled={isLoadingMore}
              type="button"
              onClick={loadMoreCases}
            >
              {isLoadingMore ? 'Loading more' : 'Load more'}
            </button>
          </div>
        )}
      </div>
    </AdminWorkspaceLayout>
  )
}

export default AdminReviewCasesPage
