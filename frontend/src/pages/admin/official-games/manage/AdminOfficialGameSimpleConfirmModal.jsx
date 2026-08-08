import { useEffect } from 'react'

function AdminOfficialGameSimpleConfirmModal({
  confirmLabel,
  description,
  isSaving,
  onClose,
  onConfirm,
  onReasonChange,
  reasonLabel,
  reasonMaxLength = 1000,
  reasonPlaceholder = '',
  reasonValue = '',
  requireReason = false,
  title,
  variant = 'primary',
}) {
  useEffect(() => {
    const originalOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        onClose()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => {
      document.body.style.overflow = originalOverflow
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [onClose])

  const confirmClassName = [
    'admin-official-button',
    variant === 'danger'
      ? 'admin-official-button--danger-solid'
      : 'admin-official-button--primary',
  ].join(' ')
  const shouldCollectReason = Boolean(onReasonChange)
  const reasonIsMissing = shouldCollectReason && requireReason && !reasonValue.trim()

  return (
    <div className="admin-official-modal-backdrop" role="presentation" onClick={onClose}>
      <section
        className="admin-official-confirm-modal admin-official-simple-confirm"
        role="dialog"
        aria-modal="true"
        aria-labelledby="admin-official-simple-confirm-title"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="admin-official-confirm-modal__copy">
          <h2 id="admin-official-simple-confirm-title">{title}</h2>
          {description && <p>{description}</p>}
        </div>

        {shouldCollectReason && (
          <label className="admin-official-textarea-field">
            <span>{reasonLabel || 'Internal reason'}</span>
            <textarea
              maxLength={reasonMaxLength}
              placeholder={reasonPlaceholder}
              value={reasonValue}
              onChange={(event) => onReasonChange(event.target.value)}
            />
            <small>{reasonValue.length}/{reasonMaxLength}</small>
          </label>
        )}

        <div className="admin-official-confirm-modal__actions">
          <button
            className="admin-official-button"
            disabled={isSaving}
            type="button"
            onClick={onClose}
          >
            Back
          </button>
          <button
            className={confirmClassName}
            disabled={isSaving || reasonIsMissing}
            type="button"
            onClick={onConfirm}
          >
            {confirmLabel}
          </button>
        </div>
      </section>
    </div>
  )
}

export default AdminOfficialGameSimpleConfirmModal
