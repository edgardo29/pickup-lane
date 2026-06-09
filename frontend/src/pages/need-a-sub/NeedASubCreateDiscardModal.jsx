import { createPortal } from 'react-dom'
import {
  dismissNeedASubBackdropMouseDown,
  useNeedASubModalDismiss,
} from './useNeedASubModalDismiss.js'

export function NeedASubCreateDiscardModal({ onClose, onDiscard }) {
  useNeedASubModalDismiss(onClose)

  return createPortal(
    <div
      className="need-sub-modal-backdrop"
      role="presentation"
      onMouseDown={(event) => dismissNeedASubBackdropMouseDown(event, onClose)}
    >
      <section
        aria-labelledby="need-sub-create-discard-title"
        aria-modal="true"
        className="need-sub-edit-discard-modal need-sub-create-discard-modal"
        role="dialog"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div>
          <h2 id="need-sub-create-discard-title">Discard post?</h2>
          <p>Your sub post has not been published. Any details you entered will be lost.</p>
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
    </div>,
    document.body,
  )
}
