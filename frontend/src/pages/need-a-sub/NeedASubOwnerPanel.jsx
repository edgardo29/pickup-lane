import { Link } from 'react-router-dom'
import {
  ClipboardList as ClipboardListIcon,
  Pencil as PencilIcon,
  Trash2 as TrashIcon,
} from 'lucide-react'
import { GameStatusIcon } from '../../components/GameFactIcons.jsx'
import { NeedASubStatusChip } from './NeedASubStatusChip.jsx'

export function NeedASubOwnerPanel({
  canCancelPost,
  canEditPost,
  canManageRequests,
  chatSection,
  onCancelPost,
  onManageRequests,
  post,
  postId,
  requests,
}) {
  const pendingRequests = requests.filter((request) => request.request_status === 'pending')
  const confirmedRequests = requests.filter((request) => request.request_status === 'confirmed')
  const waitlistedRequests = requests.filter((request) => request.request_status === 'sub_waitlist')
  const hasPendingRequests = pendingRequests.length > 0
  const spotsOpen = getPostSpotsOpen(post)
  const editTarget = `/need-a-sub/posts/${postId}/edit`

  return (
    <section className={`need-sub-manage-card need-sub-detail-card need-sub-detail-card--owner need-sub-owner-panel ${hasPendingRequests ? 'need-sub-owner-panel--urgent' : ''}`}>
      <div className="need-sub-action-card-header">
        <span className="need-sub-action-card-heading">
          <GameStatusIcon aria-hidden="true" />
          <span className="need-sub-owner-panel__eyebrow">Owner actions</span>
        </span>
        <span className="need-sub-owner-panel__header-actions">
          {hasPendingRequests && <NeedASubStatusChip>Needs review</NeedASubStatusChip>}
          <button
            aria-label="Cancel Post"
            className="need-sub-owner-panel__danger-icon"
            disabled={!canCancelPost}
            title="Cancel Post"
            type="button"
            onClick={onCancelPost}
          >
            <TrashIcon />
          </button>
        </span>
      </div>

      <div className="need-sub-owner-panel__availability">
        <span>Availability</span>
        <strong>{formatOwnerAvailability(spotsOpen)}</strong>
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

      <div className="need-sub-owner-panel__actions">
        <button
          className="need-sub-owner-panel__action need-sub-owner-panel__action--primary"
          disabled={!canManageRequests}
          type="button"
          onClick={onManageRequests}
        >
          <ClipboardListIcon />
          Manage Requests
        </button>

        {canEditPost ? (
          <Link
            className="need-sub-owner-panel__action need-sub-owner-panel__action--secondary"
            to={editTarget}
          >
            <PencilIcon />
            Edit Post
          </Link>
        ) : (
          <button
            className="need-sub-owner-panel__action need-sub-owner-panel__action--secondary"
            disabled
            type="button"
          >
            <PencilIcon />
            Edit Post
          </button>
        )}

      </div>

      {chatSection && (
        <>
          <div className="need-sub-action-card-divider" />
          <div className="need-sub-action-card-chat">
            {chatSection}
          </div>
        </>
      )}
    </section>
  )
}

function getPostSpotsOpen(post) {
  return (post?.positions || []).reduce((sum, position) => {
    const spotsOpen = Number(position.spots_needed || 0) - Number(position.confirmed_count || 0)

    return sum + Math.max(0, spotsOpen)
  }, 0)
}

function formatOwnerAvailability(spotsOpen) {
  if (spotsOpen === 0) {
    return 'No spots open'
  }

  return `${spotsOpen} ${spotsOpen === 1 ? 'spot' : 'spots'} open`
}
