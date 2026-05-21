import { Link } from 'react-router-dom'
import { NeedASubStatusChip } from './NeedASubStatusChip.jsx'

export function NeedASubOwnerPanel({ postId, requests }) {
  const pendingRequests = requests.filter((request) => request.request_status === 'pending')
  const confirmedRequests = requests.filter((request) => request.request_status === 'confirmed')
  const waitlistedRequests = requests.filter((request) => request.request_status === 'sub_waitlist')
  const hasPendingRequests = pendingRequests.length > 0
  const manageTarget = `/need-a-sub/posts/${postId}/manage`
  const reviewTarget = `${manageTarget}#requests`
  const actionTarget = hasPendingRequests ? reviewTarget : manageTarget

  return (
    <section className={`need-sub-manage-card need-sub-detail-card need-sub-detail-card--owner need-sub-owner-panel ${hasPendingRequests ? 'need-sub-owner-panel--urgent' : ''}`}>
      <div className="need-sub-action-card-header">
        <span className="need-sub-owner-panel__eyebrow">Owner actions</span>
        {hasPendingRequests && <NeedASubStatusChip>Needs review</NeedASubStatusChip>}
      </div>

      <div className="need-sub-owner-panel__stats" aria-label="Request summary">
        <span>
          <strong>{pendingRequests.length}</strong>
          <small>pending</small>
        </span>
        <span>
          <strong>{confirmedRequests.length}</strong>
          <small>confirmed</small>
        </span>
        <span>
          <strong>{waitlistedRequests.length}</strong>
          <small>waitlisted</small>
        </span>
      </div>

      <Link className="need-sub-owner-panel__primary" to={actionTarget}>
        {hasPendingRequests ? 'Review Requests' : 'Manage Post'}
      </Link>
    </section>
  )
}
