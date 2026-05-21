import {
  CalendarIcon,
  ClockIcon,
  MapPinIcon,
  UsersIcon,
} from '../../components/BrowseIcons.jsx'
import {
  buildPostSubtitle,
  formatDateWithYear,
  formatLocation,
  formatPrice,
  formatStatus,
  formatTimeRangeOnly,
} from './needASubFormatters.js'

export function NeedASubDetailHero({ post }) {
  return (
    <section className="need-sub-detail-hero need-sub-detail-card--summary">
      <div className="need-sub-detail-hero__copy">
        <div className="need-sub-detail-hero__title-row">
          <h1><HighlightedPostHeadline post={post} /></h1>
          {post.environment_type && (
            <span className="need-sub-detail-environment">
              {formatStatus(post.environment_type)}
            </span>
          )}
        </div>
        <strong>{buildPostSubtitle(post)}</strong>
        <div className="need-sub-manage-facts">
          <Fact icon={<CalendarIcon />} text={formatDateWithYear(post.starts_at)} />
          <Fact icon={<ClockIcon />} text={formatTimeRangeOnly(post)} />
          <Fact icon={<MapPinIcon />} text={formatLocation(post)} />
        </div>
      </div>

      <div className="need-sub-detail-divider" />

      <div className="need-sub-detail-summary-block">
        <p>Post Details</p>
        <div className="need-sub-detail-summary">
          <DetailSummaryItem icon={<MapPinIcon />} label="Address">
            {post.address_line_1 || 'Sign in to view exact street details'}
          </DetailSummaryItem>
          <DetailSummaryItem icon={<UsersIcon />} label="Neighborhood">
            {post.neighborhood || 'Not listed'}
          </DetailSummaryItem>
          <DetailSummaryItem icon={<PriceIcon />} label="Price due at venue">
            {formatPrice(post.price_due_at_venue_cents)}
          </DetailSummaryItem>
          {post.notes && (
            <DetailSummaryItem className="need-sub-detail-summary-item--notes" icon={<NoteIcon />} label="Notes">
              {post.notes}
            </DetailSummaryItem>
          )}
        </div>
      </div>
    </section>
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

function DetailSummaryItem({ children, className = '', icon, label }) {
  return (
    <div className={`need-sub-detail-summary-item ${className}`.trim()}>
      <span aria-hidden="true">{icon}</span>
      <div>
        <small>{label}</small>
        <strong>{children}</strong>
      </div>
    </div>
  )
}

function PriceIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 7.5v9" />
      <path d="M9.3 9.3c.7-1 2-1.3 3.3-1 1 .2 1.8.8 1.8 1.8 0 1.2-1 1.7-2.5 2-1.6.3-2.7.8-2.7 2 0 1 .9 1.7 2 1.9 1.4.3 2.8-.1 3.5-1.2" />
    </svg>
  )
}

function NoteIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M6 4.5h9l3 3v12H6Z" />
      <path d="M15 4.5v3h3" />
      <path d="M9 11h6" />
      <path d="M9 15h5" />
    </svg>
  )
}
