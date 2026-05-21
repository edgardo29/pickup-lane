import {
  BuildingIcon,
  MapPinIcon,
} from '../../components/BrowseIcons.jsx'
import darkMapPreview from '../../assets/maps/dark-map-preview.png'

export function WhereToGoCard({
  address,
  mapsUrl,
  parkingNote,
  venueName,
  mapIcon,
}) {
  const notes = [parkingNote && { icon: <ParkingIcon />, label: 'Parking', text: parkingNote }].filter(Boolean)

  return (
    <section className="details-card details-location">
      <div className="details-location__header">
        <div className="details-location__title">
          <span className="details-location__icon">{mapIcon}</span>
          <h2>Where to Go</h2>
        </div>

        {mapsUrl && (
          <a
            className="details-secondary-action details-location__map-link"
            href={mapsUrl}
            target="_blank"
            rel="noreferrer"
          >
            <span className="details-action-icon">
              <MapPinIcon />
            </span>
            <span>Open in Maps</span>
            <span className="details-action-chevron" aria-hidden="true">›</span>
          </a>
        )}
      </div>

      <div className="details-location__rows">
        <div className="details-location__row details-location__row--venue">
          <span className="details-location__note-icon">
            <BuildingIcon />
          </span>
          <div>
            <strong>Venue</strong>
            <h3>{venueName}</h3>
            <p>{address}</p>
          </div>
        </div>
      </div>

      <div className="details-location__map-preview" role="img" aria-label={`Map preview for ${venueName}`}>
        <img src={darkMapPreview} alt="" />
      </div>

      {notes.length > 0 && (
        <div className={`details-location__notes details-location__notes--${notes.length}`}>
          {notes.map((note) => (
            <div className="details-location__note" key={note.label}>
              <span className="details-location__note-icon">{note.icon}</span>
              <div>
                <strong>{note.label}</strong>
                <p>{note.text}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}

function ParkingIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="m5.2 11 1.7-4.2A2 2 0 0 1 8.8 5.5h6.4a2 2 0 0 1 1.9 1.3L18.8 11" />
      <rect x="4" y="10" width="16" height="7" rx="2" />
      <path d="M6.5 17v1.5" />
      <path d="M17.5 17v1.5" />
      <path d="M7.5 13.5h.1" />
      <path d="M16.5 13.5h.1" />
    </svg>
  )
}
