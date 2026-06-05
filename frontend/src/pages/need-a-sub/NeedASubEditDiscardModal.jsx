import {
  dismissNeedASubBackdropMouseDown,
  useNeedASubModalDismiss,
} from './useNeedASubModalDismiss.js'

export function NeedASubEditDiscardModal({ onClose, onDiscard }) {
  useNeedASubModalDismiss(onClose)

  return (
    <div
      className="need-sub-modal-backdrop"
      role="presentation"
      onMouseDown={(event) => dismissNeedASubBackdropMouseDown(event, onClose)}
    >
      <section
        aria-labelledby="need-sub-edit-discard-title"
        aria-modal="true"
        className="need-sub-edit-discard-modal"
        role="dialog"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div>
          <h2 id="need-sub-edit-discard-title">Discard changes?</h2>
          <p>Your sub post changes have not been saved.</p>
        </div>

        <div className="need-sub-edit-discard-modal__actions">
          <button className="need-sub-create-secondary" type="button" onClick={onClose}>
            Keep editing
          </button>
          <button className="need-sub-form-cancel" type="button" onClick={onDiscard}>
            Discard
          </button>
        </div>
      </section>
    </div>
  )
}
