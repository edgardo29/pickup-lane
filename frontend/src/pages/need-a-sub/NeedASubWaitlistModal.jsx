import {
  formatNeedLabel,
  getRequesterInitials,
  getRequesterName,
} from './needASubFormatters.js'

export function NeedASubWaitlistModal({ group, onClose }) {
  return (
    <div className="need-sub-modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        aria-modal="true"
        className="need-sub-waitlist-modal"
        role="dialog"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header>
          <div>
            <p>Waitlist</p>
            <h2>{formatNeedLabel(group.position)}</h2>
            <span>{group.waitlisted.length} waitlisted</span>
          </div>
          <button type="button" onClick={onClose}>
            Close
          </button>
        </header>
        <div className="need-sub-waitlist-modal__list">
          {group.waitlisted.map((request, index) => (
            <div className="need-sub-waitlist-modal__row" key={request.id}>
              <span>#{index + 1}</span>
              <span className="need-sub-manage-request__avatar" aria-hidden="true">
                {getRequesterInitials(request)}
              </span>
              <strong>{getRequesterName(request)}</strong>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
