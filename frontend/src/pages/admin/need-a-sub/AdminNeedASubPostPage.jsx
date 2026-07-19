import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  ArrowLeft,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  Eye,
  EyeOff,
  FileClock,
  MessageSquareText,
  Trash2,
  UserRound,
} from 'lucide-react'
import { FormErrorMessage } from '../../../components/FormErrorMessage.jsx'
import {
  GameDateIcon,
  GameEnvironmentIcon,
  GameFormatIcon,
  GamePlayerGroupIcon,
  GameSkillIcon,
  GameTimeIcon,
  PriceIcon,
  VenueIcon,
} from '../../../components/GameFactIcons.jsx'
import { SkeletonBlock } from '../../../components/skeleton/index.js'
import { useAuth } from '../../../hooks/useAuth.js'
import '../../../styles/admin/AdminNeedASub.css'
import AdminWorkspaceLayout from '../shared/AdminWorkspaceLayout.jsx'
import { getAdminNeedASubPost } from '../shared/adminApi.js'
import { useAdminAccess } from '../shared/useAdminAccess.js'
import AdminNeedASubChatPanel from './AdminNeedASubChatPanel.jsx'
import AdminNeedASubRemovalModal from './AdminNeedASubRemovalModal.jsx'
import {
  formatAdminNeedASubDateTime,
  formatAdminNeedASubMoney,
  formatAdminNeedASubPosition,
  formatAdminNeedASubStatus,
} from './adminNeedASubFormatters.js'

const DETAIL_PAGE_SIZE = 50
const DETAIL_TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'requests', label: 'Requests' },
  { id: 'chat', label: 'Chat' },
  { id: 'status', label: 'Status' },
  { id: 'audit', label: 'Audit' },
]

function AdminSubSection({ children, count, icon: Icon, title }) {
  return (
    <section className="admin-sub-section">
      <div className="admin-sub-section__heading">
        <div>
          <Icon />
          <h2>{title}</h2>
        </div>
        {count !== undefined && <span>{count}</span>}
      </div>
      {children}
    </section>
  )
}

function EmptyLine({ children }) {
  return <p className="admin-sub-empty-line">{children}</p>
}

function AdminSubEmptyState({ children, className = '', icon: Icon, title }) {
  const stateClassName = [
    'admin-sub-empty-state',
    className,
  ].filter(Boolean).join(' ')

  return (
    <div className={stateClassName}>
      {Icon && (
        <span className="admin-sub-empty-state__icon">
          <Icon />
        </span>
      )}
      <div>
        <strong>{title}</strong>
        {children && <p>{children}</p>}
      </div>
    </div>
  )
}

function CollectionPagination({
  label,
  limit,
  offset,
  onOffsetChange,
  pageLength,
  totalCount,
}) {
  if (totalCount <= limit) return null

  const pageStart = totalCount ? offset + 1 : 0
  const pageEnd = Math.min(offset + pageLength, totalCount)
  return (
    <nav aria-label={`${label} pagination`} className="admin-sub-pagination">
      <span>{pageStart}-{pageEnd} of {totalCount}</span>
      <div>
        <button
          aria-label={`Previous ${label} page`}
          className="admin-sub-button admin-sub-button--icon"
          disabled={offset <= 0}
          title="Previous page"
          type="button"
          onClick={() => onOffsetChange(Math.max(0, offset - limit))}
        >
          <ChevronLeft />
        </button>
        <button
          aria-label={`Next ${label} page`}
          className="admin-sub-button admin-sub-button--icon"
          disabled={offset + pageLength >= totalCount}
          title="Next page"
          type="button"
          onClick={() => onOffsetChange(offset + limit)}
        >
          <ChevronRight />
        </button>
      </div>
    </nav>
  )
}

function DetailLoading() {
  return (
    <div className="admin-sub-detail-loading" role="status" aria-label="Loading Need a Sub post">
      {Array.from({ length: 5 }).map((_, index) => (
        <section key={index}>
          <SkeletonBlock height="0.9rem" rounded width="24%" />
          <SkeletonBlock height="4rem" rounded width="100%" />
        </section>
      ))}
    </div>
  )
}

function formatAdminNeedASubDate(value, timeZone = undefined) {
  if (!value) return 'Not recorded'

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'Invalid date'

  try {
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: 'medium',
      ...(timeZone ? { timeZone } : {}),
    }).format(date)
  } catch {
    return 'Invalid date'
  }
}

function formatAdminNeedASubTime(value, timeZone = undefined) {
  if (!value) return 'Not recorded'

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'Invalid time'

  try {
    return new Intl.DateTimeFormat(undefined, {
      timeStyle: 'short',
      ...(timeZone ? { timeZone } : {}),
    }).format(date)
  } catch {
    return 'Invalid time'
  }
}

function formatAdminNeedASubTimeRange(post) {
  const start = formatAdminNeedASubTime(post.starts_at, post.timezone)
  const end = formatAdminNeedASubTime(post.ends_at, post.timezone)
  if (start === 'Not recorded' || start === 'Invalid time') return start
  if (end === 'Not recorded' || end === 'Invalid time') return start
  return `${start} - ${end}`
}

function formatNeedASubTitle(post) {
  if (!post?.subs_needed) return 'Need a Sub Post'
  return `Need ${post.subs_needed} Sub${post.subs_needed === 1 ? '' : 's'}`
}

function formatNeedASubOwner(owner) {
  return owner.display_name || owner.email || 'Unknown owner'
}

function getNeedASubAddressLines(post) {
  const cityState = [post.city, post.state].filter(Boolean).join(', ')
  const locality = [cityState, post.postal_code].filter(Boolean).join(' ')
  const lines = [post.address_line_1, locality].filter(Boolean)
  return lines.length ? lines : ['Not recorded']
}

function getNeedASubClosureReason(post) {
  return post.remove_reason || post.cancel_reason || 'No closure reason recorded.'
}

function SummaryItem({ children, icon: Icon, label }) {
  return (
    <div className="admin-sub-summary__item">
      <Icon />
      <span className="admin-sub-summary__copy">
        <small>{label}</small>
        <span className="admin-sub-summary__value">{children}</span>
      </span>
    </div>
  )
}

function PostSummary({ detail }) {
  const { post } = detail

  return (
    <section className="admin-sub-summary" aria-label="Need a Sub summary">
      <div className="admin-sub-summary__header">
        <div className="admin-sub-summary__identity">
          <span>Need a Sub</span>
          <h2>{formatNeedASubTitle(post)}</h2>
        </div>
      </div>

      <div className="admin-sub-summary__grid">
        <SummaryItem icon={GameDateIcon} label="Date">
          {formatAdminNeedASubDate(post.starts_at, post.timezone)}
        </SummaryItem>
        <SummaryItem icon={GameTimeIcon} label="Time">
          {formatAdminNeedASubTimeRange(post)}
        </SummaryItem>
        <SummaryItem icon={VenueIcon} label="Venue">
          {post.location_name || 'Not recorded'}
        </SummaryItem>
        <SummaryItem icon={GameFormatIcon} label="Format">
          {post.format_label || 'Pickup'}
        </SummaryItem>
        <SummaryItem icon={GamePlayerGroupIcon} label="Player group">
          {formatAdminNeedASubStatus(post.game_player_group)}
        </SummaryItem>
        <SummaryItem icon={GameSkillIcon} label="Skill">
          {formatAdminNeedASubStatus(post.skill_level)}
        </SummaryItem>
        <SummaryItem icon={GameEnvironmentIcon} label="Environment">
          {formatAdminNeedASubStatus(post.environment_type)}
        </SummaryItem>
        <SummaryItem icon={PriceIcon} label="Price">
          {formatAdminNeedASubMoney(post.price_due_at_venue_cents, post.currency)}
        </SummaryItem>
      </div>
    </section>
  )
}

function OverviewField({ children, label, span = 'single' }) {
  const className = [
    'admin-sub-overview-field',
    span === 'full' ? 'admin-sub-overview-field--full' : '',
  ].filter(Boolean).join(' ')

  return (
    <div className={className}>
      <span className="admin-sub-overview-field__label">{label}</span>
      <div className="admin-sub-overview-field__value">{children}</div>
    </div>
  )
}

function SubNeedsOverviewValue({ positions }) {
  if (!positions.length) return 'No sub needs found.'

  return positions.map((position) => (
    <span className="admin-sub-overview-need" key={position.id}>
      <span className="admin-sub-overview-need__name">
        {formatAdminNeedASubPosition(position.position_label, position.player_group)}
      </span>
      <span className="admin-sub-overview-need__counts">
        {position.spots_needed} needed / {position.confirmed_count} confirmed / {position.pending_count} pending / {position.sub_waitlist_count} waitlisted
      </span>
    </span>
  ))
}

function PostOverview({ detail }) {
  const { owner, post } = detail
  return (
    <section className="admin-sub-detail-panel admin-sub-record-panel admin-sub-overview-card">
      <div className="admin-sub-detail-panel__heading">
        <div>
          <ClipboardList />
          <h2>Overview</h2>
        </div>
      </div>
      {post.post_status === 'removed' && (
        <div className="admin-sub-removed-banner">
          <strong>Removed by Pickup Lane</strong>
          <span>{post.remove_reason || 'No removal reason recorded.'}</span>
        </div>
      )}
      <div className="admin-sub-overview-fields">
        <OverviewField label="Status">
          {formatAdminNeedASubStatus(post.post_status)}
        </OverviewField>
        <OverviewField label="Visibility">
          {formatAdminNeedASubStatus(post.public_visibility_status)}
        </OverviewField>
        <OverviewField label="Owner">
          {formatNeedASubOwner(owner)}
        </OverviewField>
        <OverviewField label="Sub Needs">
          <SubNeedsOverviewValue positions={post.positions ?? []} />
        </OverviewField>
        <OverviewField label="Address">
          {getNeedASubAddressLines(post).map((line) => (
            <span key={line}>{line}</span>
          ))}
        </OverviewField>
        <OverviewField label="Closure Reason" span="full">
          {getNeedASubClosureReason(post)}
        </OverviewField>
        <OverviewField label="Notes" span="full">
          {post.notes || 'No additional notes were provided.'}
        </OverviewField>
      </div>
    </section>
  )
}

function AdminNeedASubChatLocked({ isLoading }) {
  return (
    <AdminSubSection icon={MessageSquareText} title="Post Chat">
      <AdminSubEmptyState
        icon={MessageSquareText}
        title={isLoading ? 'Loading chat access' : 'Chat access required'}
      >
        {isLoading
          ? 'Loading chat access.'
          : 'Admin access is required for chat inspection.'}
      </AdminSubEmptyState>
    </AdminSubSection>
  )
}

function formatHistoryAction(item, type = 'post') {
  if (!item.old_status) {
    return type === 'request' ? 'Request created' : 'Post created'
  }
  return formatAdminNeedASubStatus(item.new_status)
}

function formatHistoryChangedBy(item) {
  if (item.changed_by?.display_name) return item.changed_by.display_name

  if (item.change_source === 'scheduled_job') return 'Scheduled job'
  if (item.change_source === 'system') return 'System'
  if (item.change_source === 'admin') return 'Admin'
  if (item.change_source === 'owner') return 'Owner'
  if (item.change_source === 'requester') return 'Requester'

  return 'System'
}

function HistoryField({ children, label }) {
  return (
    <div className="admin-sub-history-field">
      <span>{label}</span>
      {children}
    </div>
  )
}

function HistoryRows({ history, timeZone, type = 'post' }) {
  if (!history.length) return <EmptyLine>No status history found.</EmptyLine>
  return (
    <div className="admin-sub-history-list">
      {history.map((item) => (
        <div className="admin-sub-history-row" key={item.id}>
          <HistoryField label="Action">
            <strong>{formatHistoryAction(item, type)}</strong>
          </HistoryField>
          <HistoryField label="Changed by">
            <strong>{formatHistoryChangedBy(item)}</strong>
          </HistoryField>
          <HistoryField label="Reason">
            <strong>{item.change_reason || 'No reason recorded'}</strong>
          </HistoryField>
          <HistoryField label="Date">
            <time>{formatAdminNeedASubDateTime(item.created_at, timeZone)}</time>
          </HistoryField>
        </div>
      ))}
    </div>
  )
}

function StatusHistory({ history, timeZone }) {
  return (
    <AdminSubSection count={history.length} icon={FileClock} title="Status History">
      {!history.length ? (
        <AdminSubEmptyState icon={FileClock} title="No status history yet">
          Status changes will appear here once the post moves through its lifecycle.
        </AdminSubEmptyState>
      ) : (
        <HistoryRows history={history} timeZone={timeZone} />
      )}
    </AdminSubSection>
  )
}

function Requests({
  limit,
  offset,
  onOffsetChange,
  requests,
  timeZone,
  totalCount,
}) {
  return (
    <AdminSubSection count={totalCount} icon={UserRound} title="Requests">
      {!requests.length ? (
        <AdminSubEmptyState icon={UserRound} title="No requests yet">
          Sub requests will appear here once players respond to this post.
        </AdminSubEmptyState>
      ) : (
        <div className="admin-sub-request-list">
          {requests.map((request) => (
            <details key={request.id}>
              <summary>
                <div>
                  <strong>{request.requester.display_name}</strong>
                  <span>
                    {formatAdminNeedASubPosition(
                      request.position_label,
                      request.player_group,
                    )}
                  </span>
                </div>
                <div>
                  <span className={`admin-sub-status admin-sub-status--${request.request_status}`}>
                    {formatAdminNeedASubStatus(request.request_status)}
                  </span>
                  <time>{formatAdminNeedASubDateTime(request.created_at, timeZone)}</time>
                </div>
              </summary>
              <HistoryRows
                history={request.status_history}
                timeZone={timeZone}
                type="request"
              />
            </details>
          ))}
        </div>
      )}
      <CollectionPagination
        label="requests"
        limit={limit}
        offset={offset}
        onOffsetChange={onOffsetChange}
        pageLength={requests.length}
        totalCount={totalCount}
      />
    </AdminSubSection>
  )
}

function AuditActions({
  actions,
  limit,
  offset,
  onOffsetChange,
  timeZone,
  totalCount,
}) {
  return (
    <AdminSubSection count={totalCount} icon={FileClock} title="Audit History">
      {!actions.length ? (
        <AdminSubEmptyState icon={FileClock} title="No visible audit actions">
          Staff-visible audit entries will appear here once recorded.
        </AdminSubEmptyState>
      ) : (
        <div className="admin-sub-audit-list">
          {actions.map((action) => (
            <div key={action.id}>
              <strong>{formatAdminNeedASubStatus(action.action_type)}</strong>
              <span>{action.reason || 'No reason recorded'}</span>
              <span>{formatAdminNeedASubDateTime(action.created_at, timeZone)}</span>
            </div>
          ))}
        </div>
      )}
      <CollectionPagination
        label="audit actions"
        limit={limit}
        offset={offset}
        onOffsetChange={onOffsetChange}
        pageLength={actions.length}
        totalCount={totalCount}
      />
    </AdminSubSection>
  )
}

function AdminNeedASubPostPage() {
  const { postId } = useParams()
  const { currentUser } = useAuth()
  const { hasAdminAccess, isLoading: isAdminAccessLoading } = useAdminAccess()
  const [detail, setDetail] = useState(null)
  const [loadState, setLoadState] = useState('loading')
  const [pageError, setPageError] = useState('')
  const [refreshCount, setRefreshCount] = useState(0)
  const [postAction, setPostAction] = useState(null)
  const [requestOffset, setRequestOffset] = useState(0)
  const [auditOffset, setAuditOffset] = useState(0)
  const [activeTab, setActiveTab] = useState('overview')

  useEffect(() => {
    let isMounted = true

    async function loadDetail() {
      if (!currentUser || !postId) return
      setLoadState('loading')
      setPageError('')

      try {
        const response = await getAdminNeedASubPost({
          auditLimit: DETAIL_PAGE_SIZE,
          auditOffset,
          firebaseUser: currentUser,
          postId,
          requestLimit: DETAIL_PAGE_SIZE,
          requestOffset,
        })
        if (!isMounted) return
        const requestTotalCount = response.request_total_count ?? response.requests?.length ?? 0
        if (!response.requests?.length && requestOffset > 0 && requestTotalCount > 0) {
          setRequestOffset(Math.max(0, requestOffset - DETAIL_PAGE_SIZE))
          return
        }
        const auditTotalCount = response.audit_total_count ?? response.audit_actions?.length ?? 0
        if (!response.audit_actions?.length && auditOffset > 0 && auditTotalCount > 0) {
          setAuditOffset(Math.max(0, auditOffset - DETAIL_PAGE_SIZE))
          return
        }
        setDetail(response)
        setLoadState('ready')
      } catch (error) {
        if (!isMounted) return
        setDetail(null)
        setPageError(error.message || 'Need a Sub post could not be loaded.')
        setLoadState('error')
      }
    }

    loadDetail()
    return () => {
      isMounted = false
    }
  }, [auditOffset, currentUser, postId, refreshCount, requestOffset])

  const title = 'Manage Need a Sub Post'
  const canViewChat = hasAdminAccess
  const isTerminalPost = Boolean(
    detail?.post && ['removed'].includes(detail.post.post_status),
  )
  const canHidePost = Boolean(
    detail?.post &&
    !isTerminalPost &&
    detail.post.public_visibility_status === 'visible',
  )
  const canRestorePost = Boolean(
    detail?.post &&
    !isTerminalPost &&
    detail.post.public_visibility_status === 'hidden',
  )
  const canRemovePost = detail?.post && !isTerminalPost

  function handlePostActionCompleted(result) {
    setDetail((currentDetail) => {
      if (!currentDetail) return currentDetail
      return {
        ...currentDetail,
        post: {
          ...currentDetail.post,
          post_status: result.post_status,
          public_visibility_status: result.public_visibility_status,
        },
      }
    })
    setRefreshCount((count) => count + 1)
  }

  return (
    <>
      <AdminWorkspaceLayout
        actions={(
          <div className="admin-sub-header-actions">
            <Link className="admin-sub-button" to="/admin/need-a-sub">
              <ArrowLeft />
              Back
            </Link>
            {canHidePost && (
              <button
                className="admin-sub-button admin-sub-button--danger"
                type="button"
                onClick={() => setPostAction('hide')}
              >
                <EyeOff />
                Hide post
              </button>
            )}
            {canRestorePost && (
              <button
                className="admin-sub-button admin-sub-button--primary"
                type="button"
                onClick={() => setPostAction('restore')}
              >
                <Eye />
                Restore post
              </button>
            )}
            {canRemovePost && (
              <button
                className="admin-sub-button admin-sub-button--danger"
                type="button"
                onClick={() => setPostAction('remove')}
              >
                <Trash2 />
                Remove post
              </button>
            )}
          </div>
        )}
        breadcrumbs={['Admin', 'Games', 'Need a Sub']}
        description="Review sub needs, requests, chat, and moderation context."
        headerClassName="admin-sub-page-header"
        icon={ClipboardList}
        title={title}
      >
        <div className="admin-sub-detail-layout">
          {pageError && (
            <FormErrorMessage className="admin-sub-page-error">
              {pageError}
            </FormErrorMessage>
          )}
          {loadState === 'loading' ? (
            <DetailLoading />
          ) : detail ? (
            <>
              <PostSummary detail={detail} />
              <nav className="admin-sub-detail-tabs" aria-label="Need a Sub management">
                {DETAIL_TABS.map((tab) => (
                  <button
                    key={tab.id}
                    aria-selected={activeTab === tab.id}
                    className={activeTab === tab.id ? 'is-active' : ''}
                    type="button"
                    onClick={() => setActiveTab(tab.id)}
                  >
                    {tab.label}
                  </button>
                ))}
              </nav>

              {activeTab === 'overview' && (
                <div className="admin-sub-tab-panel">
                  <PostOverview detail={detail} />
                </div>
              )}

              {activeTab === 'requests' && (
                <div className="admin-sub-tab-panel">
                  <Requests
                    limit={detail.request_limit ?? DETAIL_PAGE_SIZE}
                    offset={detail.request_offset ?? requestOffset}
                    onOffsetChange={setRequestOffset}
                    requests={detail.requests ?? []}
                    timeZone={detail.post.timezone}
                    totalCount={detail.request_total_count ?? detail.requests?.length ?? 0}
                  />
                </div>
              )}

              {activeTab === 'chat' && (
                <div className="admin-sub-tab-panel">
                  {canViewChat ? (
                    <AdminNeedASubChatPanel
                      firebaseUser={currentUser}
                      postId={detail.post.id}
                      timeZone={detail.post.timezone}
                    />
                  ) : (
                    <AdminNeedASubChatLocked isLoading={isAdminAccessLoading} />
                  )}
                </div>
              )}

              {activeTab === 'status' && (
                <div className="admin-sub-tab-panel">
                  <StatusHistory
                    history={detail.post_status_history ?? []}
                    timeZone={detail.post.timezone}
                  />
                </div>
              )}

              {activeTab === 'audit' && (
                <div className="admin-sub-tab-panel">
                  <AuditActions
                    actions={detail.audit_actions ?? []}
                    limit={detail.audit_limit ?? DETAIL_PAGE_SIZE}
                    offset={detail.audit_offset ?? auditOffset}
                    onOffsetChange={setAuditOffset}
                    timeZone={detail.post.timezone}
                    totalCount={detail.audit_total_count ?? detail.audit_actions?.length ?? 0}
                  />
                </div>
              )}
            </>
          ) : null}
        </div>
      </AdminWorkspaceLayout>
      {detail && postAction && (
        <AdminNeedASubRemovalModal
          action={postAction}
          detail={detail}
          firebaseUser={currentUser}
          onClose={() => setPostAction(null)}
          onCompleted={handlePostActionCompleted}
        />
      )}
    </>
  )
}

export default AdminNeedASubPostPage
