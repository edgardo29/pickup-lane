import {
  CalendarIcon,
  ChatIcon,
  ClockIcon,
  MapPinIcon,
  PriceTagIcon,
  SoccerBallIcon,
  UsersIcon,
} from '../../../../components/BrowseIcons.jsx'
import {
  AdminCreateReviewRow,
  AdminCreateStepHeading,
} from './AdminCreateOfficialGameControls.jsx'
import {
  buildAdminOfficialGeneratedTitle,
  getAdminOfficialReview,
} from './adminCreateOfficialGameFormatters.js'

function AdminCreateOfficialGameReviewStep({ form, publishError }) {
  const review = getAdminOfficialReview(form)

  return (
    <>
      <AdminCreateStepHeading
        title="Review and create"
        text="Confirm the official listing before it becomes available to players."
      />

      <div className="admin-create-review-card">
        <AdminCreateReviewRow icon={<CalendarIcon />} label="Date" value={review.date} />
        <AdminCreateReviewRow icon={<ClockIcon />} label="Time" value={review.time} />
        <AdminCreateReviewRow icon={<SoccerBallIcon />} label="Game" value={buildAdminOfficialGeneratedTitle(form)} />
        <AdminCreateReviewRow icon={<UsersIcon />} label="Format" value={form.formatLabel} />
        <AdminCreateReviewRow icon={<UsersIcon />} label="Total spots" value={`${form.totalSpots} players`} />
        <AdminCreateReviewRow icon={<PriceTagIcon />} label="Price per player" value={review.price} />
        <hr />
        <AdminCreateReviewRow icon={<MapPinIcon />} label="Venue" value={review.venue} />
        <AdminCreateReviewRow icon={<MapPinIcon />} label="Address" value={review.address || 'Not added'} />
        <hr />
        <AdminCreateReviewRow icon={<MapPinIcon />} label="Parking note" value={form.parkingNotes || 'No parking note added.'} />
        <AdminCreateReviewRow icon={<ChatIcon />} label="Controls" value={buildControlsText(form)} />
      </div>

      {publishError && <p className="admin-create-error">{publishError}</p>}
    </>
  )
}

function buildControlsText(form) {
  return [
    form.allowGuests ? 'Guests' : 'No guests',
    form.waitlistEnabled ? 'Waitlist' : 'No waitlist',
    form.isChatEnabled ? 'Chat' : 'No chat',
  ].join(' · ')
}

export default AdminCreateOfficialGameReviewStep
