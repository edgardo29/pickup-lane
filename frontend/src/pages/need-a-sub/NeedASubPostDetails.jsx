import { Info } from 'lucide-react'
import {
  AddressIcon,
  GameDateIcon,
  GameNotesIcon,
  PriceIcon,
} from '../../components/GameFactIcons.jsx'
import {
  formatDateWithYear,
  formatPrice,
  formatTimeRangeOnly,
} from './needASubFormatters.js'
import { NeedASubDetailSectionHeading } from './NeedASubDetailSectionHeading.jsx'

export function NeedASubPostDetails({ currentUser, post }) {
  const streetLine = post.address_line_1
    ? post.address_line_1
    : currentUser
      ? 'Exact street details are not listed.'
      : 'Sign in to view exact street details.'
  const addressLine = [
    streetLine,
    [post.city, post.state, post.postal_code].filter(Boolean).join(', '),
  ].filter(Boolean).join(' · ')
  const notes = post.notes?.trim()
    || (currentUser ? 'No notes added.' : 'Sign in to view host notes.')
  const hasVenuePrice = Number(post.price_due_at_venue_cents || 0) > 0

  return (
    <section className="need-sub-detail-section need-sub-post-details-card">
      <NeedASubDetailSectionHeading eyebrow="Need To Know" icon={<Info />} />

      <div className="need-sub-post-details-grid">
        <DetailGroup className="need-sub-post-details-group--when" icon={<GameDateIcon />} title="When">
          <DetailValue label="Date">
            {formatDateWithYear(post.starts_at)}
          </DetailValue>
          <DetailValue label="Time">
            {formatTimeRangeOnly(post)}
          </DetailValue>
        </DetailGroup>

        <DetailGroup className="need-sub-post-details-group--where" icon={<AddressIcon />} title="Where">
          <DetailValue label="Venue">
            {post.location_name || 'Venue not listed'}
          </DetailValue>
          <DetailValue label="Address">
            {addressLine || 'Address not listed'}
          </DetailValue>
          {post.neighborhood && (
            <DetailValue label="Neighborhood">
              {post.neighborhood}
            </DetailValue>
          )}
        </DetailGroup>

        <DetailGroup className="need-sub-post-details-group--notes" icon={<GameNotesIcon />} title="Notes">
          <p>{notes}</p>
        </DetailGroup>

        <DetailGroup className="need-sub-post-details-group--payment" icon={<PriceIcon />} title="Payment">
          <div className="need-sub-post-details-payment">
            <small>Price</small>
            <p>
              <strong>{formatPrice(post.price_due_at_venue_cents)}</strong>
              <span>{hasVenuePrice ? '(due at venue)' : '(no payment due)'}</span>
            </p>
          </div>
        </DetailGroup>
      </div>
    </section>
  )
}

function DetailGroup({ children, className = '', icon, title }) {
  return (
    <div className={`need-sub-post-details-group ${className}`.trim()}>
      <div className="need-sub-post-details-group__header">
        <span aria-hidden="true">{icon}</span>
        <h3>{title}</h3>
      </div>
      <div className="need-sub-post-details-group__body">
        {children}
      </div>
    </div>
  )
}

function DetailValue({ children, label }) {
  return (
    <div className="need-sub-post-details-value">
      <small>{label}</small>
      <strong>{children}</strong>
    </div>
  )
}
