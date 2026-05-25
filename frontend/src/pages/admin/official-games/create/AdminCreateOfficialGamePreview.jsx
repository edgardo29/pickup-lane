import {
  BuildingIcon,
  CalendarIcon,
  ClockIcon,
  MapPinIcon,
  UsersIcon,
} from '../../../../components/BrowseIcons.jsx'
import {
  buildAdminOfficialGeneratedTitle,
  formatAdminOfficialMoney,
  getAdminOfficialReview,
} from './adminCreateOfficialGameFormatters.js'

function AdminCreateOfficialGamePreview({ form }) {
  const review = getAdminOfficialReview(form)

  return (
    <aside className="admin-create-preview" aria-label="Official game preview">
      <div className="admin-create-preview__header">
        <span>Live preview</span>
        <strong>{buildAdminOfficialGeneratedTitle(form)}</strong>
      </div>

      <div className="admin-create-preview__facts">
        <PreviewFact icon={<CalendarIcon />} label={review.date} />
        <PreviewFact icon={<ClockIcon />} label={review.time} />
        <PreviewFact icon={<MapPinIcon />} label={review.venue} />
        <PreviewFact icon={<UsersIcon />} label={`${form.totalSpots} spots · ${form.formatLabel}`} />
        <PreviewFact icon={<BuildingIcon />} label={capitalize(form.environmentType)} />
      </div>

      <div className="admin-create-preview__money">
        <span>Checkout price</span>
        <strong>{formatAdminOfficialMoney(form.price)}</strong>
      </div>

      <p className="admin-create-preview__note">
        {form.parkingNotes || 'Parking note will appear once added.'}
      </p>
    </aside>
  )
}

function PreviewFact({ icon, label }) {
  return (
    <span>
      {icon}
      {label}
    </span>
  )
}

function capitalize(value) {
  return value ? value.charAt(0).toUpperCase() + value.slice(1) : ''
}

export default AdminCreateOfficialGamePreview
