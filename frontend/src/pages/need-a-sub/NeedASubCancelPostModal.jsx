import { createPortal } from 'react-dom'
import {
  dismissNeedASubBackdropMouseDown,
  useNeedASubModalDismiss,
} from './useNeedASubModalDismiss.js'

export function NeedASubCancelPostModal({
  isCancelling,
  onClose,
  onConfirm,
}) {
  function requestClose() {
    if (!isCancelling) {
      onClose()
    }
  }

  useNeedASubModalDismiss(requestClose)

  return createPortal(
    <div
      className="need-sub-modal-backdrop"
      role="presentation"
      onMouseDown={(event) => dismissNeedASubBackdropMouseDown(event, requestClose)}
    >
      <section
        aria-labelledby="need-sub-cancel-post-title"
        aria-modal="true"
        className="need-sub-cancel-post-modal"
        role="dialog"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div>
          <h2 id="need-sub-cancel-post-title">Cancel post?</h2>
          <p>This will cancel the sub post and close any active requests.</p>
        </div>

        <div className="need-sub-cancel-post-modal__actions">
          <button
            className="need-sub-cancel-post-modal__button need-sub-cancel-post-modal__button--secondary"
            disabled={isCancelling}
            type="button"
            onClick={requestClose}
          >
            Back
          </button>
          <button
            className="need-sub-cancel-post-modal__button need-sub-cancel-post-modal__button--danger"
            disabled={isCancelling}
            type="button"
            onClick={onConfirm}
          >
            {isCancelling ? 'Canceling...' : 'Cancel Post'}
          </button>
        </div>
      </section>
    </div>,
    document.body,
  )
}
