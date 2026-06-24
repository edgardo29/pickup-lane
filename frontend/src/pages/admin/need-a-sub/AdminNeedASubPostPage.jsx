import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  ArrowLeft,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  FileClock,
  MapPin,
  RefreshCw,
  Trash2,
  UserRound,
  UsersRound,
} from 'lucide-react'
import { FormErrorMessage } from '../../../components/FormErrorMessage.jsx'
import { SkeletonBlock } from '../../../components/skeleton/index.js'
import { useAuth } from '../../../hooks/useAuth.js'
import '../../../styles/admin/AdminNeedASub.css'
import AdminWorkspaceLayout from '../shared/AdminWorkspaceLayout.jsx'
import { getAdminNeedASubPost } from '../shared/adminApi.js'
import AdminNeedASubChatPanel from './AdminNeedASubChatPanel.jsx'
import AdminNeedASubRemovalModal from './AdminNeedASubRemovalModal.jsx'
import {
  formatAdminNeedASubDateTime,
  formatAdminNeedASubMoney,
  formatAdminNeedASubPosition,
  formatAdminNeedASubStatus,
  shortAdminNeedASubId,
} from './adminNeedASubFormatters.js'

const DETAIL_PAGE_SIZE = 50

function AdminSubSection({ children, count, icon: Icon, title }) {
  return (
    <section className="admin-sub-detail-panel">
      <div className="admin-sub-detail-panel__heading">
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

function FieldGrid({ fields }) {
  return (
    <div className="admin-sub-fields">
      {fields.map((field) => (
        <div key={field.label}>
          <span>{field.label}</span>
          {field.code ? <code>{field.value}</code> : <strong>{field.value}</strong>}
        </div>
      ))}
    </div>
  )
}

function PostSummary({ detail, onRemove }) {
  const { owner, post, request_counts: counts } = detail
  const canRemove = post.post_status !== 'removed'
  return (
    <AdminSubSection icon={ClipboardList} title="Post Summary">
      {post.post_status === 'removed' && (
        <div className="admin-sub-removed-banner">
          <strong>Removed by Pickup Lane</strong>
          <span>{post.remove_reason || 'No removal reason recorded.'}</span>
        </div>
      )}
      <div className="admin-sub-kpis">
        <div>
          <span>Status</span>
          <strong>{formatAdminNeedASubStatus(post.post_status)}</strong>
        </div>
        <div>
          <span>Needed</span>
          <strong>{post.subs_needed}</strong>
        </div>
        <div>
          <span>Confirmed</span>
          <strong>{counts.confirmed_count}</strong>
        </div>
        <div>
          <span>Pending</span>
          <strong>{counts.pending_count}</strong>
        </div>
        <div>
          <span>Waitlist</span>
          <strong>{counts.waitlisted_count}</strong>
        </div>
      </div>
      <FieldGrid fields={[
        { label: 'Post ID', value: post.id, code: true },
        { label: 'Owner', value: owner.display_name },
        { label: 'Owner account', value: formatAdminNeedASubStatus(owner.account_status) },
        { label: 'Team', value: post.team_name || 'Not provided' },
        { label: 'Format', value: post.format_label },
        { label: 'Player group', value: formatAdminNeedASubStatus(post.game_player_group) },
        { label: 'Skill', value: formatAdminNeedASubStatus(post.skill_level) },
        { label: 'Environment', value: formatAdminNeedASubStatus(post.environment_type) },
      ]} />
      {canRemove && (
        <div className="admin-sub-action-strip">
          <button
            className="admin-sub-button admin-sub-button--danger"
            type="button"
            onClick={onRemove}
          >
            <Trash2 />
            Remove post
          </button>
        </div>
      )}
    </AdminSubSection>
  )
}

function ScheduleLocation({ post }) {
  return (
    <AdminSubSection icon={MapPin} title="Schedule And Location">
      <FieldGrid fields={[
        { label: 'Starts', value: formatAdminNeedASubDateTime(post.starts_at, post.timezone) },
        { label: 'Ends', value: formatAdminNeedASubDateTime(post.ends_at, post.timezone) },
        { label: 'Timezone', value: post.timezone },
        { label: 'Location', value: post.location_name },
        { label: 'Address', value: post.address_line_1 },
        { label: 'City / State', value: `${post.city}, ${post.state} ${post.postal_code}` },
        {
          label: 'Price',
          value: formatAdminNeedASubMoney(
            post.price_due_at_venue_cents,
            post.currency,
          ),
        },
        { label: 'Expires', value: formatAdminNeedASubDateTime(post.expires_at, post.timezone) },
      ]} />
      <div className="admin-sub-text-grid">
        <div>
          <span>Notes</span>
          <p>{post.notes || 'No notes recorded.'}</p>
        </div>
        <div>
          <span>Payment note</span>
          <p>{post.payment_note || 'No payment note recorded.'}</p>
        </div>
        {(post.cancel_reason || post.remove_reason) && (
          <div className="admin-sub-text-grid__wide">
            <span>Closure reason</span>
            <p>{post.remove_reason || post.cancel_reason}</p>
          </div>
        )}
      </div>
    </AdminSubSection>
  )
}

function Positions({ positions }) {
  return (
    <AdminSubSection count={positions.length} icon={UsersRound} title="Sub Needs">
      {!positions.length ? (
        <EmptyLine>No sub needs found.</EmptyLine>
      ) : (
        <div className="admin-sub-position-list">
          {positions.map((position) => (
            <div key={position.id}>
              <strong>
                {formatAdminNeedASubPosition(
                  position.position_label,
                  position.player_group,
                )}
              </strong>
              <span>{position.spots_needed} needed</span>
              <span>{position.confirmed_count} confirmed</span>
              <span>{position.pending_count} pending</span>
              <span>{position.sub_waitlist_count} waitlisted</span>
            </div>
          ))}
        </div>
      )}
    </AdminSubSection>
  )
}

function HistoryRows({ history, timeZone }) {
  if (!history.length) return <EmptyLine>No status history found.</EmptyLine>
  return (
    <div className="admin-sub-history-list">
      {history.map((item) => (
        <div key={item.id}>
          <strong>
            {formatAdminNeedASubStatus(item.old_status)} to{' '}
            {formatAdminNeedASubStatus(item.new_status)}
          </strong>
          <span>{formatAdminNeedASubStatus(item.change_source)}</span>
          <span>{item.changed_by?.display_name || 'System'}</span>
          <span>{item.change_reason || 'No reason recorded'}</span>
          <time>{formatAdminNeedASubDateTime(item.created_at, timeZone)}</time>
        </div>
      ))}
    </div>
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
        <EmptyLine>No requests found.</EmptyLine>
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
                  <code>{shortAdminNeedASubId(request.id)}</code>
                </div>
              </summary>
              <HistoryRows history={request.status_history} timeZone={timeZone} />
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
        <EmptyLine>No visible audit actions.</EmptyLine>
      ) : (
        <div className="admin-sub-audit-list">
          {actions.map((action) => (
            <div key={action.id}>
              <strong>{formatAdminNeedASubStatus(action.action_type)}</strong>
              <span>{action.reason || 'No reason recorded'}</span>
              <span>{formatAdminNeedASubDateTime(action.created_at, timeZone)}</span>
              <code>{shortAdminNeedASubId(action.id)}</code>
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
  const [detail, setDetail] = useState(null)
  const [loadState, setLoadState] = useState('loading')
  const [pageError, setPageError] = useState('')
  const [refreshCount, setRefreshCount] = useState(0)
  const [isRemovalModalOpen, setIsRemovalModalOpen] = useState(false)
  const [requestOffset, setRequestOffset] = useState(0)
  const [auditOffset, setAuditOffset] = useState(0)

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

  const title = detail?.post?.team_name || 'Need a Sub Post'

  return (
    <>
      <AdminWorkspaceLayout
        actions={(
          <div className="admin-sub-header-actions">
            <Link className="admin-sub-button" to="/admin/need-a-sub">
              <ArrowLeft />
              Back
            </Link>
            <button
              aria-label="Refresh Need a Sub post"
              className="admin-sub-button admin-sub-button--icon"
              type="button"
              onClick={() => setRefreshCount((count) => count + 1)}
            >
              <RefreshCw />
            </button>
          </div>
        )}
        breadcrumbs={['Admin', 'Games', 'Need a Sub']}
        description="Review post, requests, chat, and moderation context."
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
              <div className="admin-sub-detail-grid">
                <PostSummary
                  detail={detail}
                  onRemove={() => setIsRemovalModalOpen(true)}
                />
                <Positions positions={detail.post.positions ?? []} />
              </div>
              <ScheduleLocation post={detail.post} />
              <Requests
                limit={detail.request_limit ?? DETAIL_PAGE_SIZE}
                offset={detail.request_offset ?? requestOffset}
                onOffsetChange={setRequestOffset}
                requests={detail.requests ?? []}
                timeZone={detail.post.timezone}
                totalCount={detail.request_total_count ?? detail.requests?.length ?? 0}
              />
              <AdminNeedASubChatPanel
                firebaseUser={currentUser}
                postId={detail.post.id}
                timeZone={detail.post.timezone}
                onModerated={() => setRefreshCount((count) => count + 1)}
              />
              <AdminSubSection
                count={detail.post_status_history?.length ?? 0}
                icon={FileClock}
                title="Post Status History"
              >
                <HistoryRows
                  history={detail.post_status_history ?? []}
                  timeZone={detail.post.timezone}
                />
              </AdminSubSection>
              <AuditActions
                actions={detail.audit_actions ?? []}
                limit={detail.audit_limit ?? DETAIL_PAGE_SIZE}
                offset={detail.audit_offset ?? auditOffset}
                onOffsetChange={setAuditOffset}
                timeZone={detail.post.timezone}
                totalCount={detail.audit_total_count ?? detail.audit_actions?.length ?? 0}
              />
            </>
          ) : null}
        </div>
      </AdminWorkspaceLayout>
      {detail && isRemovalModalOpen && (
        <AdminNeedASubRemovalModal
          detail={detail}
          firebaseUser={currentUser}
          onClose={() => setIsRemovalModalOpen(false)}
          onRemoved={() => setRefreshCount((count) => count + 1)}
        />
      )}
    </>
  )
}

export default AdminNeedASubPostPage
