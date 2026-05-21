import {
  CalendarIcon,
  ClockIcon,
  MapPinIcon,
  PencilIcon,
  TrashIcon,
  UsersIcon,
} from '../../components/BrowseIcons.jsx'
import {
  buildPostSubtitle,
  formatDateWithYear,
  formatStatus,
  formatTimeRangeOnly,
} from './needASubFormatters.js'
import NeedASubRequestReview from './NeedASubRequestReview.jsx'

function NeedASubManageReview({
  activeRequestStatus,
  canCancelPost,
  onAcceptRequest,
  onBeginEdit,
  onCancelPost,
  onCloseWaitlistModal,
  onDeclineRequest,
  onRemoveRequest,
  onSelectPosition,
  onStatusChange,
  onViewWaitlist,
  post,
  requestGroups,
  selectedGroup,
  waitlistModalGroup,
}) {
  return (
    <>
      <section className="need-sub-manage-hero">
        <div className="need-sub-manage-hero__summary">
          <span className="need-sub-manage-hero__icon" aria-hidden="true">
            <UsersIcon />
          </span>
          <div className="need-sub-manage-hero__copy">
            <div className="need-sub-detail-hero__title-row">
              <h1><HighlightedPostHeadline post={post} /></h1>
              {post.environment_type && (
                <span className="need-sub-detail-environment">
                  {formatStatus(post.environment_type)}
                </span>
              )}
            </div>
            <strong className="need-sub-manage-subtitle">{buildPostSubtitle(post)}</strong>
            <div className="need-sub-manage-facts">
              <Fact icon={<CalendarIcon />} text={formatDateWithYear(post.starts_at)} />
              <Fact icon={<ClockIcon />} text={formatTimeRangeOnly(post)} />
              <Fact icon={<MapPinIcon />} text={`${post.location_name} · ${post.city}, ${post.state}`} />
            </div>
          </div>
        </div>

        <div className="need-sub-manage-actions">
          <button type="button" onClick={onBeginEdit}>
            <PencilIcon />
            Edit
          </button>
          <button
            className="need-sub-danger-action"
            disabled={!canCancelPost}
            type="button"
            onClick={onCancelPost}
          >
            <TrashIcon />
            Cancel
          </button>
        </div>
      </section>

      <NeedASubRequestReview
        activeRequestStatus={activeRequestStatus}
        onAcceptRequest={onAcceptRequest}
        onCloseWaitlistModal={onCloseWaitlistModal}
        onDeclineRequest={onDeclineRequest}
        onRemoveRequest={onRemoveRequest}
        onSelectPosition={onSelectPosition}
        onStatusChange={onStatusChange}
        onViewWaitlist={onViewWaitlist}
        requestGroups={requestGroups}
        selectedGroup={selectedGroup}
        waitlistModalGroup={waitlistModalGroup}
      />
    </>
  )
}

function HighlightedPostHeadline({ post }) {
  return (
    <>
      Need <span>{post.subs_needed}</span> {post.subs_needed === 1 ? 'Sub' : 'Subs'}
    </>
  )
}

function Fact({ icon, text }) {
  return (
    <span>
      {icon}
      {text}
    </span>
  )
}

export default NeedASubManageReview
