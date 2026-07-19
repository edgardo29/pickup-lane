import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  ArrowLeft,
  ClipboardList,
  FileClock,
  RefreshCw,
  UserRound,
} from 'lucide-react'
import { FormErrorMessage } from '../../../components/FormErrorMessage.jsx'
import { useAuth } from '../../../hooks/useAuth.js'
import '../../../styles/admin/AdminNeedASub.css'
import AdminWorkspaceLayout from '../shared/AdminWorkspaceLayout.jsx'
import { getAdminNeedASubRequest } from '../shared/adminApi.js'
import {
  formatAdminNeedASubDateTime,
  formatAdminNeedASubPosition,
  formatAdminNeedASubStatus,
  shortAdminNeedASubId,
} from './adminNeedASubFormatters.js'

function RequestField({ label, value }) {
  return (
    <div className="admin-sub-field">
      <span>{label}</span>
      <strong>{value || 'None'}</strong>
    </div>
  )
}

function RequestCodeField({ label, value }) {
  return (
    <div className="admin-sub-field">
      <span>{label}</span>
      <code>{value || 'None'}</code>
    </div>
  )
}

function StatusHistory({ entries }) {
  if (!entries.length) {
    return <p className="admin-sub-empty-line">No status history.</p>
  }

  return (
    <div className="admin-sub-history-list">
      {entries.map((entry) => (
        <div key={entry.id}>
          <strong>{formatAdminNeedASubStatus(entry.new_status)}</strong>
          <span>{formatAdminNeedASubDateTime(entry.created_at)}</span>
          <span>{entry.change_reason || 'No reason recorded'}</span>
        </div>
      ))}
    </div>
  )
}

function AdminNeedASubRequestPage() {
  const { requestId } = useParams()
  const { currentUser } = useAuth()
  const [detail, setDetail] = useState(null)
  const [loadState, setLoadState] = useState('loading')
  const [pageError, setPageError] = useState('')
  const [refreshCount, setRefreshCount] = useState(0)

  useEffect(() => {
    let isMounted = true

    async function loadRequest() {
      if (!currentUser || !requestId) return

      setLoadState('loading')
      setPageError('')

      try {
        const nextDetail = await getAdminNeedASubRequest({
          firebaseUser: currentUser,
          requestId,
        })
        if (!isMounted) return

        setDetail(nextDetail)
        setLoadState('ready')
      } catch (error) {
        if (!isMounted) return

        setDetail(null)
        setPageError(error.message || 'Need a Sub request could not be loaded.')
        setLoadState('error')
      }
    }

    loadRequest()

    return () => {
      isMounted = false
    }
  }, [currentUser, requestId, refreshCount])

  const post = detail?.post
  const request = detail?.request
  const pageTitle = request
    ? `Request ${shortAdminNeedASubId(request.id)}`
    : 'Need a Sub Request'

  return (
    <AdminWorkspaceLayout
      breadcrumbs={['Admin', 'Games', 'Need a Sub']}
      description="Inspect a Need a Sub request and its moderation context."
      headerClassName="admin-sub-page-header"
      icon={ClipboardList}
      title={pageTitle}
    >
      <div className="admin-sub-detail-layout">
        <div className="admin-sub-header-actions">
          <Link className="admin-sub-button" to={post ? `/admin/need-a-sub/${post.id}` : '/admin/need-a-sub'}>
            <ArrowLeft />
            {post ? 'Post' : 'Need a Sub'}
          </Link>
          <button
            className="admin-sub-button"
            type="button"
            onClick={() => setRefreshCount((count) => count + 1)}
          >
            <RefreshCw />
            Refresh
          </button>
        </div>

        {pageError && (
          <FormErrorMessage className="admin-sub-page-error">
            {pageError}
          </FormErrorMessage>
        )}

        {loadState === 'loading' && (
          <section className="admin-sub-section">
            <p className="admin-sub-empty-line">Loading request.</p>
          </section>
        )}

        {loadState === 'ready' && detail && request && post && (
          <>
            <section className="admin-sub-section">
              <div className="admin-sub-section__heading">
                <div>
                  <UserRound />
                  <h2>Request</h2>
                </div>
              </div>
              <div className="admin-sub-field-list admin-sub-field-list--three">
                <RequestField
                  label="Status"
                  value={formatAdminNeedASubStatus(request.request_status)}
                />
                <RequestField
                  label="Position"
                  value={formatAdminNeedASubPosition(
                    request.position_label,
                    request.player_group,
                  )}
                />
                <RequestField
                  label="Requester"
                  value={request.requester?.display_name}
                />
                <RequestCodeField label="Request ID" value={request.id} />
                <RequestCodeField label="Post ID" value={post.id} />
                <RequestField
                  label="Created"
                  value={formatAdminNeedASubDateTime(request.created_at)}
                />
              </div>
            </section>

            <section className="admin-sub-section">
              <div className="admin-sub-section__heading">
                <div>
                  <ClipboardList />
                  <h2>Post Context</h2>
                </div>
              </div>
              <div className="admin-sub-field-list admin-sub-field-list--three">
                <RequestField
                  label="Post status"
                  value={formatAdminNeedASubStatus(post.post_status)}
                />
                <RequestField
                  label="Visibility"
                  value={formatAdminNeedASubStatus(post.public_visibility_status)}
                />
                <RequestField
                  label="Starts"
                  value={formatAdminNeedASubDateTime(post.starts_at, post.timezone)}
                />
              </div>
            </section>

            <section className="admin-sub-section">
              <div className="admin-sub-section__heading">
                <div>
                  <FileClock />
                  <h2>Status History</h2>
                </div>
                <span>{request.status_history?.length ?? 0}</span>
              </div>
              <StatusHistory entries={request.status_history ?? []} />
            </section>
          </>
        )}
      </div>
    </AdminWorkspaceLayout>
  )
}

export default AdminNeedASubRequestPage
