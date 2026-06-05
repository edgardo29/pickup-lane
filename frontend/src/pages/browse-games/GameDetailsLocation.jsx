import { AddressIcon, ParkingIcon, VenueIcon } from '../../components/GameFactIcons.jsx'
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
              <AddressIcon />
            </span>
            <span>Open in Maps</span>
          </a>
        )}
      </div>

      <div className="details-location__rows">
        <div className="details-location__row details-location__row--venue">
          <span className="details-location__note-icon">
            <VenueIcon />
          </span>
          <div>
            <strong>Venue</strong>
            <h3>{venueName}</h3>
          </div>
        </div>

        {address && (
          <div className="details-location__row details-location__row--address">
            <span className="details-location__note-icon">
              <AddressIcon />
            </span>
            <div>
              <strong>Address</strong>
              <p>{address}</p>
            </div>
          </div>
        )}
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
